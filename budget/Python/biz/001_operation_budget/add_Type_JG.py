try:
    from _debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
import pandas as pd


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# 获取技改计划信息
def get_plancode_data(tabname, columns, path, year, entity):
    sql_obj = DataTableMySQL(tabname, path=path)
    t = sql_obj.table
    where = (t.Year == year) & (t.Entity_Opreation == entity)
    df = sql_obj.select(where=where, columns=columns)
    return df

# 获取设备信息
def get_equipment_data(tabname, columns, path, year, entity):
    sql_obj = DataTableMySQL(tabname, path=path)
    t = sql_obj.table
    where = (t.year == year) & (t.entity == entity) & (t.plancode.notnull())
    df = sql_obj.select(where=where, columns=columns)
    return df


# 修改profile表中的技改类型
# def update_profile_Type_JG():
    # print(2)


def main(p1,p2):
    print(p2)
    year = p2["year"]
    entity = p2["entity"]
    jg_columns = ["Year","Entity_Opreation","PLANCODE","PROJ_TYPE"]
    jg_Type_dt = get_plancode_data('Opreation_JG',jg_columns,'/Datatable/BCP_Table',year, entity)
    # print(jg_Type_dt)
    # print(1)

    profile_columns = ["year", "entity", "code","plancode"]
    profile_dt = get_equipment_data('equipment_profile', profile_columns, '/Datatable/Equipment', year, entity)
    # print(profile_dt)

    dt_filtered = pd.merge(profile_dt,jg_Type_dt,how='left', left_on='plancode',right_on='PLANCODE')
    # print(dt_filtered)

    dt_finall = dt_filtered[dt_filtered['PROJ_TYPE'].notna()]

    # 保留 code 和 PROJ_TYPE 两列，并重命名 PROJ_TYPE 为 Type_JG
    dt_result = dt_finall[['code', 'PROJ_TYPE']].rename(columns={'PROJ_TYPE': 'Type_JG'})
    print(dt_result)

    profile_table = DataTableMySQL("equipment_profile")
    profile_table.insert_df(dt_result, ['Type_JG'])



if __name__ == '__main__':
    para2 = {'year': '2025', 'entity': 'Y6120210005', 'department': 'HR', 'equipment_location': 'el01', 'sheetName': 'Sheet1', 'sheetId': 'SHTfc2afe475f28', 'elementName': 'sh_equipment_big_fix', 'folderId': 'DIR493c22b46ab3'}

    main(para1,para2)
