# -*- coding: utf-8 -*-
'''
@file    : act_access.py
@Time    :
@Author  : CHENJL
@Software: PyCharm
@Desc    : 北控水务 接口数据操作主入口 涉及：主数据（Entity、Material），实际数
'''

try:
    from common._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
import pandas as pd
import datetime
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

# from biz.config._debug import para1
def fun_query_mysql(where, table_nm, path_table):
    # mysql 实例化
    client = MySQLClient()
    # mysql查询
    sql_01 = "select * from ${%s} %s" % (table_nm, where)
    df_table = client.query_dfs(sqls=sql_01,
                                table_info={table_nm: {'elementName': table_nm,
                                                       'elementType': 'DataTableMySQL',
                                                       'path': path_table}})
    return df_table


def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/02_Dimension')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
    del df['id']
    del df['expectedName']
    df = df.where(df.notnull(), None)
    return df


def fun_cube(df, BudYear, cube_bewg, p2):
    if p2['year'] == '空':
        # 不输入参数，相当于全年月1-12
        Period = ''
        for value in range(1, 13):
            Period += str(value) + ';'
        Period = Period + 'Noperiod'
        # Period = Period[:-1]
    elif p2['year'] != '空':
        # 输入参数，指定月份删除
        Period = ''
        for value in range(int(p2['month_begin']), int(p2['month_end']) + 1):
            Period += str(value) + ';'
        Period = Period + 'Noperiod'
        # Period = Period[:-1]
    # 数据操作cube
    # 先删
    fix_del = "Year{%s}->Scenario{Actual}->Version{Y1}->Period{%s}->Tax{Tax;Notax}->Allocation{Original}->" \
              "Misc1{Nomisc1}->Misc2{Nomisc2}" % (str(int(BudYear) - 1), Period)
    if p2['entity'] != '空':
        fix_del += '->Entity{%s}' % ";".join(set(df['Entity'].to_list()))
    d = cube_bewg.delete(fix_del)
    # 后插
    i = cube_bewg.save(df)
    print(1)


def query_actual_data(p2):
    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/03_Variable')
    BudYear = variable.get('BudYear')
    # 不传参默认 处理 预算年-1的1-9 + （预算年-2的10-12）并置年为预算年-1
    if p2['year'] == '空':
        year_1 = str(int(BudYear) - 1)
        year_2 = str(int(BudYear) - 2)
        Year = year_1 + ',' + year_2
        month_begin = '1'
        month_end = '12'
    elif p2['year'] != '空' and p2['month_begin'] != '空' and p2['month_end'] != '空':
        Year = p2['year']
        month_begin = p2['month_begin']
        month_end = p2['month_end']
        BudYear = str(int(p2['year']) + 1)
    # 初始化
    table = DataTableMySQL('bewg_actual_data')
    columns = ['Entity_code', 'Material_code', 'Account_code', 'Measure_code', 'Year', 'Period', 'Tax_code', 'Figure',
               'Data_source']
    where = "Year in (%s) and ((Period >= '%s' and Period <= '%s') or Period = 99)" % (
        Year, month_begin, month_end)
    # 判断是否传入组织查询
    if p2['entity'] != '空':
        # where += f"and Entity_code in ('{p2['entity']}') "
        # 特殊处理 传参 ps取 IBase
        entity = ''
        for i in p2['entity'].split(","):
            entity += 'IBase(%s,0);' % i
        entity = entity[:-1]
        print('entity',entity)
        df_entity = fun_qurey_dimension('Entity', entity, ['name'])
        entity = "','".join(set(df_entity['name'].to_list()))
        entity = entity.replace('_', '-')
        where += "and Entity_code in ('%s')" % entity
    df_ods = table.select_raw(columns=columns, where=where)
    print(df_ods)
    df_ods = pd.DataFrame.from_dict(df_ods)
    print('df_ods',df_ods)
    df_ods = df_ods.rename(columns={"Entity_code": "Entity", "Material_code": "Material", "Account_code": "Account",
                                    "Measure_code": "Measure", "Tax_code": "Tax", "Figure": "data"})
    # 单独获取 期间为 99 的数据
    df_ods.loc[df_ods['Period'] == 99, 'Period'] = 'Noperiod'

    # 处理问题数据 空
    df_ods.loc[df_ods['Measure'].isnull(), 'Measure'] = ''
    df_ods.loc[df_ods['Material'] == 'null', 'Material'] = ''
    df_ods.loc[df_ods['Tax'] == 'tax', 'Tax'] = 'Tax'

    df_ods['Year'] = df_ods['Year'].astype(str)
    df_ods['Period'] = df_ods['Period'].astype(str)
    # df_ods.to_excel(r"D:\FH-company\FH_WORK\北控水务业务预算\测试数据\111.xlsx", index=False)
    return df_ods, BudYear


def calc_rate(cube_bewg, BudYear, df_lk):
    # 处理税率问题
    fix_rate = "Year{%s}->Scenario{Actual}->Version{Y1}->Period{Remove(Base(TotalPeriod,0),Adjust)}->Material{Nomaterial;01;02;03;04;05;98;99}->" \
               "Tax{Taxrate}->Allocation{Original}->Department{Operation}->Measure{Nomeasure;Expenses}->" \
               "Misc1{Nomisc1}->Misc2{Nomisc2}" % str(int(BudYear) - 1)
    df_rate = cube_bewg.query(fix_rate, compact=False)
    # 收入类的科目
    list_sr = ['PL01010101','PL01010102','PL01010103',
               # 新收入科目只算不含税全年合计
               'PL01010201','PL01010202','PL010103','PL010104','PL010105','PL010106','PL010107','PL010108','PL010109',
               'PL010110','PL010111','PL010112','PL010113','PL010114','PL010115','PL010116',
               # 把设备类的科目也按照项目层级 计算税率
               'PL0102040101','PL010204010201','PL010204010202','PL010204010203','PL0102040201','PL0102040202','PL0102040203',
               'YW0202','YW0104','YW0101','YW0102'
               ]

    # 管报收入科目税率
    df_lk_sr = pd.merge(df_lk[df_lk['Account'].isin(list_sr)],
                        df_rate[['Account', 'Period', 'Version', 'Entity', 'Measure', 'data']].rename(
                            columns={"data": "rate_data"}), how='left')

    # 管报水量税率
    list_nan = ['YW0101', 'YW0102', 'YW0202' ,'YW0104', 'YW0108']
    df_lk_sr.loc[df_lk_sr['Account'].isin(list_nan), 'rate_data'] = None


    # 成本类科目 税率取虚拟水厂的税率
    df_entity = fun_qurey_dimension('Entity', 'Base(1,0)', ['name', 'parent_name'])
    df_entity = df_entity[['name', 'parent_name']]

    df_rate = pd.merge(df_rate[~df_rate['Account'].isin(list_sr)], df_entity.rename(
        columns={"name": "Entity"}), how='left')
    df_lk_cb = pd.merge(df_lk[~df_lk['Account'].isin(list_sr)], df_entity.rename(
        columns={"name": "Entity"}), how='left')
    df_lk_cb['Year'] = df_lk_cb['Year'].astype('str')
    df_rate['Year'] = df_rate['Year'].astype('str')
    df_lk_cb = pd.merge(df_lk_cb, df_rate[['Account', 'Period', 'parent_name', 'Version', 'data']].rename(
        columns={"data": "rate_data"}), how='left')
    df_lk_cb = pd.merge(df_lk_cb, df_entity[df_entity['name'].str.startswith('XN')], how='left')
    print("df_lk_cb",df_lk_cb)
    # 兰科 成本类的项目数据 赋值在虚拟子水厂上
    df_lk_cb = pd.merge(df_lk_cb, df_entity[df_entity['name'].str.startswith('XN')], how='left')
    df_lk_cb.loc[~df_lk_cb['name'].isnull(), 'Entity'] = df_lk_cb['name']
    print('第二次df_lk_cb',df_lk_cb)
    del df_lk_cb['name']
    # 合并收入、成本数据
    df_lk = df_lk_sr.append(df_lk_cb).reset_index(drop=True, inplace=False)

    # 计算逻辑：Tax = NOtax * （1 + Taxrate）；
    df_lk.loc[((df_lk['Tax'] == 'Notax') & (
        ~df_lk['rate_data'].isnull())), 'data'] = \
        df_lk['data'] * (1 + df_lk['rate_data'])
    df_lk['Tax'] = 'Tax'
    del df_lk['rate_data']
    del df_lk['Data_source']
    del df_lk['parent_name']

    # 数据汇总有用吗
    df_lk = \
    df_lk.groupby(['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax', 'Allocation', 'Account',
                   'Department', 'Measure', 'Misc1', 'Misc2'], as_index=False)['data'].sum()
    print('df_lk汇总',df_lk)
    print('df_entity',df_entity)

    return df_lk, df_entity, list_sr


def fun_actual_data(cube_bewg, p2):
    # 一、获取实际数中间表数据
    df, BudYear = query_actual_data(p2)
    df = df.reset_index(drop=True, inplace=False)
    # 处理Entity的中间杠替换成下划线杠 '—' 替换为 '_'
    df.loc[df['Entity'].str.contains('-'), 'Entity'] = df['Entity'].apply(lambda x: x.replace('-', '_'))
    # 映射组织 处理中间表数据与entity维度映射
    table_nm = 'Entity_mapping'
    path_table = '/05_Datatable/05_09_Actual/'
    where = ''
    df_entity_mapping = fun_query_mysql(where, table_nm, path_table)
    print(df_entity_mapping)
    df = pd.merge(df, df_entity_mapping[['Entity', 'Entity_code']].rename(
        columns={"Entity": "Entity_map", "Entity_code": "Entity"}), how='left')
    df.loc[df['Entity_map'].notnull(), 'Entity'] = df['Entity_map']
    print('df',df)
    del df['Entity_map']

    # 二、获取实际数映射表数据
    table_nm = 'bewg_actual_mapping'
    path_table = '/05_Datatable/05_09_Actual/'
    where = ''
    df_mapping = fun_query_mysql(where, table_nm, path_table)
    map_account_list = list(set(df_mapping['Account'].to_list()))
    # 限定科目范围(映射表)
    df = df[df['Account'].isin(map_account_list)]
    # 限定科目范围(维度)
    account_list_isin = fun_qurey_dimension('Account', 'Base(#root,0)', ['name'])
    account_list_isin = list(set(account_list_isin['name'].to_list()))
    df = df[df['Account'].isin(account_list_isin)]
    print(df)

    # 限定Entity范围
    df_entity = fun_qurey_dimension('Entity', 'Base(1,0)', ['name'])
    print(df_entity)
    entity_list = list(set(df_entity['name'].to_list()))
    df = df[df['Entity'].isin(entity_list)]

    # 三、处理条线 获取科目维度数据 Account 用来判断 条线的映射关系
    # （1）设备条线的用Equipment
    df_account = fun_qurey_dimension('Account', 'IDescendant(PL010204,0)', ['name'])
    account_list_eqp = df_account['name'].to_list()
    del df_account
    # （2）人力条线的用HR（暂时没有）
    df_account = fun_qurey_dimension('Account', 'IDescendant(PL0103,0)', ['name'])
    account_list_hr = df_account['name'].to_list()
    # 合并特殊处理的两个list
    account_list = account_list_eqp + account_list_hr
    # 映射逻辑处理
    df['Scenario'] = 'Actual'
    df['Version'] = 'Y1'
    df['Allocation'] = 'Original'
    df['Misc1'] = 'Nomisc1'
    df['Misc2'] = 'Nomisc2'
    df.loc[df['Material'] == '', 'Material'] = 'Nomaterial'
    # 处理 条线
    df.loc[df['Account'].isin(account_list_eqp), 'Department'] = 'Equipment'
    df.loc[df['Account'].isin(account_list_hr), 'Department'] = 'HR'
    # （3）处理设备和人力条线其余都是运行条线
    df.loc[~df['Account'].isin(account_list), 'Department'] = 'Operation'

    # 四、处理度量维度
    # （1）提取度量不为空的数据 进水、出水
    df_measure_notnull = df[df['Measure'] != '']
    # （2）提取运行天数，sed（T0059）度量为Nomeasure；管报（T0109）度量为Expenses
    df_measure_null = df[((df['Measure'] == '') & (df['Account'].isin(['YW0202'])))]
    df_measure_account = df[((df['Measure'] == '') & (~df['Account'].isin(['YW0202'])))]
    df_measure_null.loc[df_measure_null['Data_source'] == 'T0059', 'Measure'] = 'Nomeasure'
    df_measure_null.loc[df_measure_null['Data_source'] == 'T0109', 'Measure'] = 'Expenses'
    # （3）提取其余的度量为空的去bewg_actual_mapping里做科目与度量的映射
    df_measure_account = pd.merge(df_measure_account, df_mapping[['Measure_code', 'Account']].rename(
        columns={"Measure_code": "Measure_map"}), how='left')
    del df_measure_account['Measure']
    df_measure_account = df_measure_account.rename(columns={"Measure_map": "Measure"})
    del df
    # （4）最后整合到df
    df = df_measure_notnull.append(df_measure_null).append(df_measure_account).reset_index(drop=True, inplace=False)


    # # 3、如果为空，当数据来源为SED时，则为Policy。 update 注释 20221015
    # df.loc[((df['Measure'] == '') & (df_measure_null['Data_source'] == 'SED')), 'Measure'] = 'Policy'

    # 五、处理税率 只针对管报数据做处理 管报 T0109
    df_lk = df[df['Data_source'] == 'T0109']
    df_lk, df_entity, list_sr = calc_rate(cube_bewg, BudYear, df_lk)

    # 本身基础上增加管报含税数据
    df = df.append(df_lk).reset_index(drop=True, inplace=False)

    # 为啥要加这个？？？？
    df = df.where(df.notnull(), 'T0109')


    # 六、处理物料/科目映射 目前针对 管报原材料费用/sed一厂一侧
    table_nm = 'Material_mapping'
    path_table = '/05_Datatable/05_09_Actual/'
    where = ''
    df_t077_material = fun_query_mysql(where, table_nm, path_table)
    df = pd.merge(df, df_t077_material[['Account_code', 'Material', 'Account', 'Data_source']].rename(
        columns={"Account_code": "Account", "Material": "Material_code", "Account": "Account_code"}), how='left')
    df.loc[df['Material_code'].notnull(), 'Material'] = df['Material_code']
    df.loc[df['Account_code'].notnull(), 'Account'] = df['Account_code']

    del df['Material_code']
    del df['Account_code']

    # 单独获取管报T0109 不含税成本类 科目 数据
    df_lk_notax = df[((df['Tax'] == 'Notax') & (df['Data_source'] == 'T0109') & (~df['Account'].isin(list_sr)))]
    print("df_lk_notax",df_lk_notax)
    # 剔除 管报 不含税成本类 科目 数据
    df = df[~((df['Tax'] == 'Notax') & (df['Data_source'] == 'T0109') & (~df['Account'].isin(list_sr)))]

    # 这里因为不需要赋值到虚拟子水厂上了 ，所以先注释掉 陈晶磊241018
    # # 管报 不含税成本科目类数据 赋值在虚拟子水厂上
    df_lk_notax = pd.merge(df_lk_notax.rename(columns={"Entity": "name"}), df_entity, how='left')
    df_lk_notax = pd.merge(df_lk_notax.rename(columns={"name": "Entity"}),
                           df_entity[df_entity['name'].str.startswith('XN')], how='left')
    df_lk_notax.loc[~df_lk_notax['name'].isnull(), 'Entity'] = df_lk_notax['name']
    print("第二次df_lk_notax", df_lk_notax)
    del df_lk_notax['name']
    del df_lk_notax['parent_name']


    # 拼接兰科不含税成本类数据
    df = df.append(df_lk_notax).reset_index(drop=True, inplace=False)

    # 七、获取实际数物料映射表数据 处理物料映射关系
    table_nm = 'bewg_material_mapping'
    path_table = '/05_Datatable/05_09_Actual'
    where = ''
    df_mapping_material = fun_query_mysql(where, table_nm, path_table)
    df = pd.merge(df, df_mapping_material[['Material', 'Material_code']], how='left')
    df = df.where(df.notnull(), None)
    df.loc[df['Material_code'].notnull(), 'Material'] = df['Material_code']
    del df['Material_code']

    # 限定物料范围
    df_material = fun_qurey_dimension('Material', 'Base(#root,0)', ['name'])
    material_list = list(set(df_material['name'].to_list()))
    df = df[df['Material'].isin(material_list)]

    # sed一厂一策存在子水厂吗？
    # 单独处理 数据来源为：T0059且科目为：'A93','A94','A95','A96','A97','A98','A100';范围的数据直接写到PS组织上 20221015 新增
    df_t0059 = df[((df['Data_source'] == 'T0059') & (df['Account'].isin(
        ['YW0701', 'YW0702', 'YW0703', 'YW0704', 'YW0705', 'YW0706', 'YW0707'])))]

    df_t0059 = pd.merge(df_t0059, df_entity.rename(columns={"name": "Entity"}), how='left')
    df_t0059.loc[~df_t0059['parent_name'].isnull(), 'Entity'] = df_t0059['parent_name']
    del df_t0059['parent_name']
    # 合并 T0059 PS数据


    df = df.append(df_t0059).reset_index(drop=True)

    # 将汇总改为不汇总而是删除列
    # df = df.drop(['Data_source'], axis=1)
    df = df.groupby(['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax', 'Allocation', 'Account',
                     'Department', 'Measure', 'Misc1', 'Misc2'], as_index=False)['data'].sum()
    print('进cube之前的df',df)
    # 操作cube
    fun_cube(df, BudYear, cube_bewg, p2)
    return BudYear


def calc_year(df_index, index, p2):
    if df_index['Year'][index] == 'POV':
        year = p2['Year']
    elif df_index['Year'][index] == 'POV-1':
        year = str(int(p2['Year']) - 1)
    elif df_index['Year'][index] == 'POV-2':
        year = str(int(p2['Year']) - 2)
    elif df_index['Year'][index] == 'POV-3':
        year = str(int(p2['Year']) - 3)
    return year


def query_cube(df_index, year, cube_bewg, index, Entity):
    df = cube_bewg.query(
        "Year{%s}->Account{%s}->Scenario{%s}->Measure{%s}->Tax{%s}->Version{%s}->Department{%s}->"
        "Period{%s}->Material{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->Entity{%s}"
        % (year, df_index['Account'][index], df_index['Scenario'][index], df_index['Measure'][index],
           df_index['Tax'][index], df_index['Version'][index], df_index['Department'][index], df_index['Period'][index],
           df_index['Material'][index], df_index['Allocation'][index], df_index['Misc1'][index],
           df_index['Misc2'][index],
           Entity), compact=False)
    # 列命名
    df = df.rename(columns={"data": df_index['calc'][index]})
    # 筛选字段
    df = df[['Entity', 'Period', 'Material', '%s' % df_index['calc'][index]]]
    return df


def del_cube(df_index, cube_bewg, index, year, Entity):
    fix_del = "Year{%s}->Account{%s}->Scenario{%s}->Measure{%s}->Tax{%s}->Version{%s}->Department{%s}->Period{%s}->Material{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->Entity{%s}" % (
    year, df_index['Account'][index], df_index['Scenario'][index], df_index['Measure'][index], df_index['Tax'][index],
    df_index['Version'][index], df_index['Department'][index], df_index['Period'][index], df_index['Material'][index],
    df_index['Allocation'][index], df_index['Misc1'][index], df_index['Misc2'][index], Entity)
    cube_bewg.delete(fix_del)


def insert_cube(df_index, df_outer, year, index):
    if df_index['calc'][index] == 'A/B':
        df_insert = df_outer[['Entity', 'Period', 'Material', 'data']]
    elif df_index['calc'][index] == 'Σ(A*B)/C':
        df_insert = df_outer[['Entity', 'Material', 'data']]
    if ((df_index['form'][index] == '吨水电耗')
            or (df_index['form'][index] == '吨水电费-年')
            or (df_index['form'][index] == '污泥处理费吨水费用-年')
            or (df_index['calc'][index] == 'Σ(A*B)/C')):
        df_index = df_index[['Account', 'Scenario', 'Measure', 'Tax', 'Version',
                             'Department', 'Allocation', 'Misc1', 'Misc2', 'Period']]
    else:
        df_index = df_index[['Account', 'Scenario', 'Measure', 'Tax', 'Version',
                             'Department', 'Allocation', 'Misc1', 'Misc2']]
    for (columnName, columnData) in df_index.iteritems():
        # print(columnName,columnData)
        df_insert[columnName] = df_index[columnName][index]
    # 给定年份
    df_insert['Year'] = year
    return df_insert


def df_save(df_insert_all, cube_bewg):
    # 数据存入cube
    cube_bewg.save(df_insert_all)


# 相关指标也直接接入 不计算2025.7.1
def calc_actual(BudYear, cube_bewg, p2):
    year = str(int(BudYear) - 1)
    print(year)
    # 获取配置数据
    path_table = '/05_Datatable/05_09_Actual'
    table_nm = 'audit_analysi_calc_exp'
    where = "where source = 'Actual'"
    df_mapping = fun_query_mysql(where, table_nm, path_table)
    print(df_mapping)
    del table_nm, path_table, where
    # 获取次sheet需要处理的科目种类
    form_list = list(set(df_mapping['form'].to_list()))
    # 获取本批次全部待插入数据
    df_insert_all = pd.DataFrame()
    for form in form_list:
        # 限定本次处理的范围 dml 排序 重置索引
        df_mapping_form = df_mapping[df_mapping['form'] == form].sort_values(
            by='dml', ascending=False, inplace=False).reset_index(drop=True)
        # 初始化 df
        df_outer = pd.DataFrame()
        df_insert = pd.DataFrame()
        # 根据指标判断 Entity处理范围
        if p2['entity'] == '空':
            entity = 'Base(1,0)'
            print(entity)
        elif p2['entity'] != '空':
            entity = ''
            for i in p2['entity'].split(","):
                entity += 'Base(%s,0);' % i
            entity = entity[:-1]
        df_entity = fun_qurey_dimension('Entity', entity, ['name'])
        print(df_entity)
        if df_mapping_form['form'][0] == '日保底水量':
            Entity = ";".join(list(set(df_entity[~df_entity['name'].str.startswith('XN')]['name'].to_list())))
        else:
            Entity = ";".join(list(set(df_entity[df_entity['name'].str.startswith('XN')]['name'].to_list())))
        # 根据行索引 分次处理
        for index in list(df_mapping_form.index):
            df_index = df_mapping_form.iloc[[index]]
            # 根据DML类型判断处理，insert、select
            if df_index['dml'][index] == 'select':
                df_query = query_cube(df_index, year, cube_bewg, index, Entity)
                # 拼接列
                if not df_outer.empty:
                    # 单独处理 原材料吨干泥成本（元/吨干泥）、原材料吨水成本（元/吨）
                    if ((df_index['form'][index] == '原材料吨干泥成本（元/吨干泥）') or
                            (df_index['form'][index] == '原材料吨水成本（元/吨）')):
                        df_query = df_query.drop(columns={'Material'})
                    df_outer = pd.merge(df_outer, df_query, how='outer')
                    df_outer = df_outer.fillna(0)
                    # 单独处理 原材料吨干泥成本（元/吨干泥）、原材料吨水成本（元/吨）
                    if ((df_index['form'][index] == '原材料吨干泥成本（元/吨干泥）') or
                            (df_index['form'][index] == '原材料吨水成本（元/吨）')):
                        df_outer = df_outer[df_outer['Material'] != 0]
                if index == 0:
                    df_outer = df_query
            elif not df_outer.empty:
                # insert 分计算类型 分别处理
                if df_index['calc'][index] == 'A/B':
                    # 调用删除逻辑
                    del_cube(df_index, cube_bewg, index, year, Entity)
                    df_outer = df_outer[df_outer['B'] != 0]
                    df_outer.loc[df_outer['Entity'] != '', 'data'] = df_outer['A'] / df_outer['B']
                    if ((df_index['form'][index] == '运输单价（实际数）') or
                            (df_index['form'][index] == '处置单价（实际数）')):
                        # 原材料单价 * 10000 单独处理 20221107 增加 mud_cost_ton
                        df_outer.loc[df_outer['Entity'] != '', 'data'] = df_outer['data'] * 10000
                elif df_index['calc'][index] == 'Σ(A*B)/C':
                    # 调用删除逻辑
                    del_cube(df_index, cube_bewg, index, year, Entity)
                    # 分别处理两个计算因子
                    # 1、先算 Σ（A*B）
                    df_left = df_outer[df_outer['Period'] != 'TotalPeriod']
                    df_left.loc[df_left['Entity'].notnull(), 'data'] = df_left['A'] * df_left['B']
                    df_left = df_left.groupby(['Entity'], as_index=False)['data'].sum()
                    # 2、再算 C
                    df_right = df_outer[df_outer['Period'] == 'TotalPeriod'][['Entity', 'Material', 'C']]
                    # 3、计算 Σ（A*B）/ C
                    df_outer = pd.merge(df_left, df_right, how='left')
                    df_outer.loc[df_outer['Entity'].notnull(), 'data'] = df_outer['data'] / df_outer['C']

                elif df_index['calc'][index] == 'A-B':
                    pass

                # 获取待插入数据
                df_outer_insert = insert_cube(df_index, df_outer, year, index)
                df_insert = df_insert.append(df_outer_insert)
        # append
        df_insert_all = df_insert_all.append(df_insert)

    if not df_insert_all.empty:
        # 数据存储

        df_save(df_insert_all, cube_bewg)


def main(p1, p2):
    p2 = {'func': '实际数', 'year': '空', 'month_end': '1', 'month_begin': '12', 'entity': '空'}
    try:
        print(p2)
        cube_bewg = FinancialCube('WS_cube', path='/01_Cube')
        if p2['func'] == '实际数':
            # 实际数 存cube
            BudYear = fun_actual_data(cube_bewg, p2)
            print('123')
            # 处理实际数指标
            # BudYear = '2025'
            #
            calc_actual(BudYear, cube_bewg, p2)
            print(BudYear)
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    # p1 = {}
    # p2 = {'func': "实际数", 'year': "空", 'month_begin': "1", 'month_end': "12", 'entity': "空"}
    main(para1, para2)


