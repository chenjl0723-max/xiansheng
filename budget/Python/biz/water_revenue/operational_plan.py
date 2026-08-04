from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
import pandas as pd
import copy

# added by wlm
# added in 20220822
# added for 经营计划数进入水价与收入维度
# 获取数据的字段列表
columns = ['Item', 'Department', 'Year', 'Scenario', 'Version', 'Price_before_adjust', 'Price_adjust',
           'ExceedPrice_before_adjust', 'ExceedPrice_adjust', 'Yield_before_adjust', 'Yield_adjust',
           'Price_InitialDate', 'Yield_InitialDate', 'Price_increase', 'Yield', 'Yield_increase', 'Price']
# 获取数据表名
tab_name = 'BCP'
# 获取数据表路径
path = '/Datatable/BCP_Table'


# step0 获取数据
def get_operation_data(tbl, columns, path, param):
    sql_obj = DataTableMySQL(tbl, path=path)
    t = sql_obj.table
    # (t.year == year) & (t.entity == entity)
    where = (t.Entity == param['Entity']) & (t.Department == param['Department']) & (t.Year == param['Year']) & (
            t.Scenario == param['Scenario']) & (t.Version == param['Version'])
    df = sql_obj.select(where=where, columns=columns)

    # df = df[(df["Item"] != "1213001500") & (df["Item"] != "1213001200") & (df["Item"] != "1213001700")]
    return df


# step1 计算逻辑
def cacl_operation(dt_oper):
    # 复制一个原表出来，后边保存cube用
    dt_oper_copy = dt_oper.copy()
    # 计算日期的月份及日期
    dt_oper["Price_InitialDate"] = pd.to_datetime(dt_oper["Price_InitialDate"])

    Price_InitialDate_year = dt_oper["Price_InitialDate"].dt.year
    Price_InitialDate_month = dt_oper['Price_InitialDate'].dt.month
    Price_InitialDate_day = dt_oper['Price_InitialDate'].dt.day

    dt_oper["Yield_InitialDate"] = pd.to_datetime(dt_oper["Yield_InitialDate"])

    Yield_InitialDate_year = dt_oper["Yield_InitialDate"].dt.year
    Yield_InitialDate_month = dt_oper['Yield_InitialDate'].dt.month
    Yield_InitialDate_day = dt_oper['Yield_InitialDate'].dt.day
    # 将计算的月份日期添加到DataFrame中
    dt_oper['Price_InitialDate_month'] = Price_InitialDate_month
    dt_oper['Price_InitialDate_day'] = Price_InitialDate_day
    dt_oper['Yield_InitialDate_month'] = Yield_InitialDate_month
    dt_oper['Yield_InitialDate_day'] = Yield_InitialDate_day
    dt_oper["Price_InitialDate_year"] = Price_InitialDate_year
    dt_oper["Yield_InitialDate_year"] = Yield_InitialDate_year

    dt_oper.loc[dt_oper["Price_InitialDate_year"].isna(), "Price_InitialDate_year"] = dt_oper["Year"]
    dt_oper.loc[dt_oper["Yield_InitialDate_year"].isna(), "Yield_InitialDate_year"] = dt_oper["Year"]

    dt_oper['Price_InitialDate_month'] = dt_oper['Price_InitialDate_month'].astype("int", errors="ignore")
    dt_oper['Price_InitialDate_day'] = dt_oper['Price_InitialDate_day'].astype("int", errors="ignore")
    dt_oper['Yield_InitialDate_month'] = dt_oper['Yield_InitialDate_month'].astype("int", errors="ignore")
    dt_oper['Yield_InitialDate_day'] = dt_oper['Yield_InitialDate_day'].astype("int", errors="ignore")
    dt_oper["Price_InitialDate_year"] = dt_oper["Price_InitialDate_year"].astype("int", errors="ignore")
    dt_oper["Yield_InitialDate_year"] = dt_oper["Yield_InitialDate_year"].astype("int", errors="ignore")
    dt_oper["Year"] = dt_oper["Year"].astype("int", errors="ignore")

    # # dt_oper = dt_oper.fillna(0)
    # dt_oper["Price_InitialDate_year"] = dt_oper["Price_InitialDate_year"].astype(int).astype(str)
    # dt_oper["Yield_InitialDate_year"] = dt_oper["Yield_InitialDate_year"].astype(int).astype(str)
    # 根据日期计算；小于等于15号：当前月份到12月取Price_adjust ；大于15号当前月份+1 到12月份取Price_adjust

    # 判断月份
    dt_oper.loc[(dt_oper['Price_InitialDate_day'] <= 15) & (
            dt_oper["Price_InitialDate_year"].astype(int) == dt_oper["Year"].astype(int)), 'initial_month'] = dt_oper[
        'Price_InitialDate_month']
    dt_oper.loc[(dt_oper['Price_InitialDate_day'] > 15) & (
            dt_oper["Price_InitialDate_year"].astype(int) == dt_oper["Year"].astype(int)), 'initial_month'] = dt_oper[
                                                                                                                  'Price_InitialDate_month'] + 1
    dt_oper.loc[(dt_oper['Yield_InitialDate_day'] <= 15) & (
            dt_oper["Yield_InitialDate_year"] == dt_oper["Year"]), 'yield_month'] = dt_oper[
        'Yield_InitialDate_month']
    dt_oper.loc[(dt_oper['Yield_InitialDate_day'] > 15) & (
            dt_oper["Yield_InitialDate_year"] == dt_oper["Year"]), 'yield_month'] = dt_oper[
                                                                                        'Yield_InitialDate_month'] + 1
    dt_oper['key'] = 1
    # 与月份关联
    dt_month = pd.DataFrame(data={'month': [i for i in range(1, 13)], 'key': 1})
    dt_oper = pd.merge(left=dt_oper, right=dt_month, how='left', on='key')
    # 判断月份计算值
    dt_oper['YW0105'] = dt_oper['Price_adjust']
    dt_oper.loc[
        (dt_oper['month'] < dt_oper['initial_month']), 'YW0105'] = dt_oper['Price_before_adjust']

    dt_oper['YW0108'] = dt_oper['ExceedPrice_adjust']
    dt_oper.loc[
        (dt_oper['month'] < dt_oper['initial_month']), 'YW0108'] = dt_oper['ExceedPrice_before_adjust']

    dt_oper['YW0107'] = dt_oper['Yield_adjust']
    dt_oper.loc[(dt_oper['month'] < dt_oper['yield_month']), 'YW0107'] = \
        dt_oper['Yield_before_adjust']

    # 判断水价调整年份，大于POV年份取before，否则取ExceedPrice_adjust
    # 判断水价调整年份，大于POV年份取before，否则取ExceedPrice_adjust
    dt_oper.loc[(dt_oper["Price_InitialDate_year"].astype(int) > dt_oper["Year"].astype(int)) | (
        pd.isnull(dt_oper['Price_InitialDate_day'])), "YW0105"] = dt_oper[
        'Price_before_adjust']
    dt_oper.loc[dt_oper["Price_InitialDate_year"] < dt_oper["Year"], "YW0105"] = dt_oper[
        'Price_adjust']

    dt_oper.loc[(dt_oper["Price_InitialDate_year"] > dt_oper["Year"]) | (
        pd.isnull(dt_oper['Price_InitialDate_day'])), "YW0108"] = dt_oper[
        'ExceedPrice_before_adjust']
    dt_oper.loc[dt_oper["Price_InitialDate_year"] < dt_oper["Year"], "YW0108"] = dt_oper[
        'ExceedPrice_adjust']

    # 判断保底水量调整年份，大于POV年份，则取before 否则取Yield_adjust
    dt_oper.loc[(dt_oper["Yield_InitialDate_year"] > dt_oper["Year"]) | (
        dt_oper['Yield_InitialDate_day'].isna()), "YW0107"] = dt_oper[
        'Yield_before_adjust']
    dt_oper.loc[dt_oper["Yield_InitialDate_year"] < dt_oper["Year"], "YW0107"] = dt_oper[
        'Yield_adjust']

    columns = ['Item', 'Department', 'Year', 'Scenario', 'Version', 'month', 'YW0105', 'YW0108', 'YW0107']
    dt_oper = dt_oper[columns].rename(columns={'Item': 'Entity', 'month': 'Period'})
    # 新增需求，将取出的字段保存到Cube的科目中
    dt_oper_copy = dt_oper_copy.rename(
        columns={'Price': 'YW0601', 'Price_before_adjust': 'YW0602', 'Price_adjust': 'YW0603', 'Price_increase': 'YW0604',
                 'Price_InitialDate': 'YW0605', 'Yield': 'YW0606', 'Yield_before_adjust': 'YW0607', 'Yield_adjust': 'YW0608',
                 'Yield_increase': 'YW0609', 'Yield_InitialDate': 'YW0610'})
    columns = ['Item', 'Department', 'Year', 'Scenario', 'Version', 'YW0601', 'YW0602', 'YW0603', 'YW0604', 'YW0605', 'YW0606',
               'YW0607', 'YW0608', 'YW0609', 'YW0610']
    dt_oper_copy = dt_oper_copy[columns].rename(columns={'Item': 'Entity'})

    return dt_oper, dt_oper_copy


# step1 数据进入cube
def save_operation(dt_oper, pov, del_fix):
    if dt_oper.size > 0:
        # 先清数
        cube = FinancialCube('WS_cube', path='/01_Cube')
        cube.delete(del_fix)
        # 保存数据
        response = cube.save_unpivot(dt_oper, pov=pov, unpivot_dim='Account')
        return response


def main(p1, p2, dt_oper=pd.DataFrame()):
    if dt_oper.empty:
        # 获取经营计划中的数据
        dt_oper = get_operation_data(tab_name, columns, path, p2)
        if dt_oper.size > 0:
            # 获取计算后的数据，dt_oper为第一次保存数据；dt_oper_copy为第二次新增保存数据
            dt_oper, dt_oper_copy = cacl_operation(dt_oper)
            # 拼接要删除
            list_entity = list(set(dt_oper['Entity'].tolist()))
            list_entity = ';'.join(list_entity)
            pov = {'Measure': 'Expenses', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax',
                   'Misc1': 'Nomisc1',
                   'Misc2': 'Nomisc2'}
            pov_copy = {'Period': 'TotalPeriod', 'Measure': 'Revenue', 'Material': 'Nomaterial',
                        'Allocation': 'Original',
                        'Tax': 'Default',
                        'Misc1': 'Nomisc1',
                        'Misc2': 'Nomisc2'}
            del_fix = copy.deepcopy(pov)
            del_fix['Entity'] = "Base(%s,0)" % p2['Entity']  # list_entity
            del_fix['Department'] = p2['Department']
            del_fix['Year'] = p2['Year']
            del_fix['Scenario'] = p2['Scenario']
            del_fix['Version'] = p2['Version']
            del_fix['Account'] = 'YW0105;YW0108;YW0107'
            del_fix['Period'] = '1;2;3;4;5;6;7;8;9;10;11;12'
            response = save_operation(dt_oper, pov, del_fix)

            del_fix_copy = del_fix.copy()
            del_fix_copy['Account'] = 'YW0601;YW0602;YW0603;YW0604;YW0605;YW0606;YW0607;YW0608;YW0609;YW0610'
            del_fix_copy['Period'] = 'TotalPeriod'
            del_fix_copy['Measure'] = 'Revenue'
            del_fix_copy['Tax'] = 'Default'
            dt_oper_copy["YW0605"] = dt_oper_copy.YW0605.astype(str).where(dt_oper_copy.YW0605.notnull(), None)
            dt_oper_copy["YW0610"] = dt_oper_copy.YW0610.astype(str).where(dt_oper_copy.YW0610.notnull(), None)

            def func(item):
                if item == "1":
                    return "是"
                elif item == "2":
                    return "否"

            dt_oper_copy['YW0601'] = dt_oper_copy['YW0601'].apply(func)
            dt_oper_copy['YW0606'] = dt_oper_copy['YW0606'].apply(func)
            response_copy = save_operation(dt_oper_copy, pov_copy, del_fix_copy)
            print(response, response_copy)
    else:
        # 获取经营计划中的数据
        # dt_oper = get_operation_data(tbl= tab_name, columns=columns, path=path, param=p2)
        if dt_oper.size > 0:
            # 获取计算后的数据，dt_oper为第一次保存数据；dt_oper_copy为第二次新增保存数据
            dt_oper, dt_oper_copy = cacl_operation(dt_oper)
            # 拼接要删除的
            list_entity = list(set(dt_oper['Entity'].tolist()))
            list_entity = ';'.join(list_entity)
            list_year = list(set(dt_oper['Year'].tolist()))

            pov = {'Measure': 'Expenses', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax',
                   'Misc1': 'Nomisc1',
                   'Misc2': 'Nomisc2'}
            pov_copy = {'Period': 'TotalPeriod', 'Measure': 'Revenue', 'Material': 'Nomaterial',
                        'Allocation': 'Original',
                        'Tax': 'Default',
                        'Misc1': 'Nomisc1',
                        'Misc2': 'Nomisc2'}
            del_fix = copy.deepcopy(pov)
            del_fix['Department'] = "Operation"
            del_fix['Scenario'] = "Budget"
            del_fix['Version'] = 'Y1'
            del_fix['Account'] = 'YW0105;YW0108;YW0107'
            del_fix['Period'] = '1;2;3;4;5;6;7;8;9;10;11;12'

            del_fix_copy = del_fix.copy()
            del_fix_copy['Account'] = 'YW0601;YW0602;YW0603;YW0604;YW0605;YW0606;YW0607;YW0608;YW0609;YW0610'
            del_fix_copy['Period'] = 'TotalPeriod'
            del_fix_copy['Measure'] = 'Revenue'
            del_fix_copy['Tax'] = 'Default'
            dt_oper_copy["YW0605"] = dt_oper_copy.YW0605.astype(str).where(dt_oper_copy.YW0605.notnull(), None)
            dt_oper_copy["YW0610"] = dt_oper_copy.YW0610.astype(str).where(dt_oper_copy.YW0610.notnull(), None)

            def func(item):
                if item == "1":
                    return "是"
                elif item == "2":
                    return "否"

            dt_oper_copy['YW0601'] = dt_oper_copy['YW0601'].apply(func)
            dt_oper_copy['YW0606'] = dt_oper_copy['YW0606'].apply(func)

            for i in list_year:
                # year = list_year[i]
                entity = list(set(dt_oper[dt_oper['Year'] == i]['Entity'].to_list()))
                entity = ';'.join(entity)
                year = str(i)

                del_fix["Year"] = year
                del_fix["Entity"] = entity
                response = save_operation(dt_oper, pov, del_fix)

                del_fix_copy["Year"] = year
                del_fix_copy["Entity"] = entity
                response_copy = save_operation(dt_oper_copy, pov_copy, del_fix_copy)

                print(response, response_copy)


if __name__ == '__main__':
    try:
        from common._debug import para1, p2
    except:
        pass
    main(para1, p2)
