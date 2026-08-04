# 原材料填报有效成分 ——非集采

import sys
sys.path.append('../../')
# from bksw.conf._evn import p1, p2

from deepfos.element.finmodel import FinancialCube
from deepfos.db.mysql import MySQLClient
from deepfos.element.dimension import Dimension
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# 获取原材料数据
def get_material_data(fix):
    client = MySQLClient()
    dt_material = pd.DataFrame()
    print(fix)
    sql = """
        SELECT
	material.Entity,
	material.Ingredient AS Material,
	material.Active,
	CASE
    WHEN material.COD IS NULL THEN
    	basic.COD
    ELSE
    	material.COD
    END AS cod,
     CASE
    WHEN material.TN IS NULL THEN
    	basic.TN
    ELSE
    	material.TN
    END AS tn,
     CASE
    WHEN material.Coefficient IS NULL THEN
    	basic.Coefficient
    ELSE
    	material.Coefficient
    END AS coefficient,
     CASE
    WHEN material.Equivalent IS NULL THEN
    	basic.Equivalent
    ELSE
    	material.Equivalent
    END AS Equivalent,
     material.UnitPrice,
     material.`Year`,
     material.Department,
     material.Scenario,
     material.Version
    FROM
    	${Material_Submit} AS material
    LEFT OUTER JOIN ${Material_BasicData} AS basic ON material.Ingredient = basic.Ingredient
    AND material.Year = basic.Year

    LEFT OUTER JOIN ${Material_Information} AS infor ON material.Entity = infor.Entity
    AND material.Ingredient = infor.Ingredient
    LEFT OUTER JOIN ${Material_Information_copy} AS mation ON material.Entity = mation.Entity
    AND material.Ingredient = mation.Ingredient
        where material.`Year`='{year}' and material.Department='{department}'
        and material.Scenario='{scenario}' and material.Version='{version}'
            """.format(year=fix["Year_wb1"], department=fix['Department_wb1'], scenario=fix['Scenario_wb1'],
                       version=fix['Version_wb1'], Material_Submit="{Material_Submit}",
                       Material_BasicData="{Material_BasicData}", Material_Information="{Material_Information}",
                       Material_Information_copy="{Material_Information_copy}")

    if fix['Entity_wb1'] != 'IDescendant(1,0)':
        sql += " and material.Entity='{entity}'".format(entity=fix["Entity_wb1"])

    dt_material = client.query_dfs(sqls=sql)
    print(dt_material)
    return dt_material


# 获取维度成员
def get_dimension():
    dim = Dimension('Material', path='/02_Dimension')
    org2 = dim.query('Base(MQ02,0)', as_model=False, fields=['name'])
    dt_dim = pd.DataFrame(org2).rename(columns={'name': 'Material'})
    return dt_dim


# 判断字段取正确的值
def calc_material_data(dt_material):
    if dt_material.size == 0:
        return
    dt_dim = get_dimension()
    # 拼接默认维度
    dt_material['Measure'] = 'Expenses'
    dt_material['Allocation'] = 'Original'
    dt_material['Tax'] = 'Tax'
    dt_material['Misc1'] = 'Nomisc1'
    dt_material['Misc2'] = 'Nomisc2'
    dt_material['key'] = 1
    dt_month = pd.DataFrame(data={"Period": [str(i) for i in range(1, 13)], 'key': 1})
    dt_month = dt_month.append({"Period": "Noperiod", "key": 1}, ignore_index=True).reset_index()
    # 关联月份表，生成1-12月份的数据
    dt_material = pd.merge(left=dt_material, right=dt_month, how='left', on='key')
    del dt_material['key']
    del dt_material["index"]

    dt_material_dim = dt_material.rename(
        columns={'Active': 'YW0302', 'cod': 'YW0307', 'tn': 'YW0308', 'coefficient': 'YW0317', 'Equivalent': 'YW0311',
                 'UnitPrice': 'YW0303'})

    return dt_material_dim


def main(p1, p2):
    # 获取需要计算的物料信息
    dt_material = get_material_data(p2)
    # 判断字段是否为空并赋予正确的字段值
    cube = FinancialCube("WS_cube", path='/01_Cube/')
    year = str(int(p2['Year_wb1']) - 1)
    # 查询YW0304 YW0316
    budget_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0316;YW0304}->Scenario{%s}->" \
              "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Tax{Tax}->Year{%s}" % (
                  p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], p2['Scenario_wb1'], p2['Year_wb1'])
    budget_df = cube.query(expression=budget_fix, compact=False, pivot_dim='Account')
    print(budget_df)

    forcast_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0316;YW0304}->Scenario{Forecast}->" \
              "Measure{Expenses}->Period{10;11;12}->Tax{Tax}->Year{%s}" % (
              p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], year)
    forcast_df = cube.query(expression=forcast_fix, compact=False, pivot_dim='Account')

    actual_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0316;YW0304}->Scenario{Actual}->" \
              "Measure{Expenses}->Period{Noperiod}->Tax{Tax}->Year{%s}" % (
                  p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], year)
    actual_df = cube.query(expression=actual_fix, compact=False, pivot_dim='Account')

    df_YW0304_YW0316 = pd.concat([budget_df, forcast_df, actual_df])

    # 拼接删除fix   ;Material{}}
    del_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0302;YW0307;YW0308;YW0317;YW0311;YW0303;YW0316;YW0304}->Scenario{%s}->" \
              "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Tax{Tax}->Year{%s}" % (
                  p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], p2['Scenario_wb1'], p2['Year_wb1'])
    # 删除数据
    cube.delete(del_fix)

    del_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0302;YW0307;YW0308;YW0317;YW0311;YW0303;YW0316;YW0304}->Scenario{Forecast}->" \
              "Measure{Expenses}->Period{10;11;12}->Tax{Tax}->Year{%s}" % (
              p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], year)
    # 删除数据
    cube.delete(del_fix)
    del_fix = "Entity{%s}->Material{NAndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->Department{%s}->Version{%s}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0302;YW0307;YW0308;YW0317;YW0311;YW0303;YW0316;YW0304}->Scenario{Actual}->" \
              "Measure{Expenses}->Period{Noperiod}->Tax{Tax}->Year{%s}" % (
                  p2['Entity_wb1'], p2['Department_wb1'], p2['Version_wb1'], year)
    # 删除数据
    cube.delete(del_fix)
    if dt_material.size == 0:
        return

    dt_material1 = calc_material_data(dt_material)
    print(dt_material)
    # 保存数据
    df_forecast = dt_material1[dt_material1['Period'].isin(["10", "11", "12"])]
    df_forecast['Year'] = year
    df_forecast['Scenario'] = 'Forecast'
    df_actual = dt_material1[dt_material1['Period']=='Noperiod']
    df_actual['Year'] = year
    df_actual['Scenario'] = 'Actual'

    df_baf = pd.concat([dt_material1, df_forecast, df_actual])
    print('df_baf',df_baf)
    cube.save_unpivot(data=df_baf, unpivot_dim='Account')
    df_baf = df_baf[['Entity', 'Material', 'YW0303', 'Year',
       'Department', 'Scenario', 'Version', 'Measure', 'Allocation', 'Tax',
       'Misc1', 'Misc2', 'Period']]
    df_baf = df_baf[~df_baf['Material'].isnull()]
    df_baf = df_baf[~df_baf['Entity'].isnull()]
    df_baf = pd.merge(df_baf,df_YW0304_YW0316 , how='left').fillna(0)
    diff_list = list({"YW0304", "YW0316"}.difference(df_baf.columns))
    if diff_list:
        df_baf[diff_list] = [0] * len(diff_list)
    df_baf = df_baf[~df_baf['YW0303'].isnull()]
    df_baf = df_baf[df_baf['YW0303']!=0]
    del df_baf['YW0303']
    if not df_baf.empty:
        print('df_baf2',df_baf)
        cube.save_unpivot(data=df_baf, unpivot_dim='Account')


if __name__ == '__main__':

    # 原材料采集脚本-非集采
    try:
        from common.__debug import para1
    except:
        pass
    para2 = {'elementName': '_Material_Unit', 'folderId': 'DIRacd99f1aefd0', 'sheetName': '原材料单耗填报（非集采药剂）', 'sheetId': 'SHTdb258039787a486589a8827c08a1eafb', 'Year_wb1': '2026', 'Entity_wb1': 'XN43002_01', 'Department_wb1': 'Operation', 'Tax_wb1': 'Tax', 'Version_wb1': 'Y1', 'Material_wb1': 'Nomaterial', 'Allocation_wb1': 'Original', 'Measure_wb1': 'Expenses', 'Misc1_wb1': 'Nomisc1', 'Misc2_wb1': 'Nomisc2'}
    main(para1, para2)
