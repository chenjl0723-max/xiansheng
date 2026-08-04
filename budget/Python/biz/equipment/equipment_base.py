# 日常维护费基线
# 取出cube里子水厂的运营规模
# 取出entity_zt_new表中的运营驻场时间，用变量年-运营驻场时间 = 运营年限
# 根据这两个指标计算出子水厂的基线


from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
import pandas as pd
from datetime import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

def calculate_life_years(df):
    """
    计算运营年限 = 当前年份 - 运营驻场时间年
    参数：
        df: DataFrame，包含 sub_factory_code 和 Years_in_service（日期格式）
    返回：
        DataFrame 包含 life_years 列
    """
    year = Variable('Variable').get('BudYear')

    # 确保 Years_in_service 是日期格式，提取年份
    df['Years_in_service'] = pd.to_datetime(df['Years_in_service'], errors='coerce')
    df['start_year'] = df['Years_in_service'].dt.year.fillna(0).astype(int)
    # 计算运营年限
    df['life_years'] = int(year) - df['start_year']
    # 错误数据补0
    df['life_years'] = df['life_years'].clip(lower=0)
    # 清除多余列，重命名，去重
    df = df.drop(columns=['start_year', 'Years_in_service'])
    df = df.rename(columns={'sub_factory_code': 'Entity'})
    df['Entity'] = df['Entity'].str.replace('-', '_')
    df = df.drop_duplicates(subset=['Entity'])
    print(df)
    return df


def calculate_baseline(df):
    """
    根据运营规模和年限计算日常维护费基线
    参数：
        df: DataFrame，包含 operation_scale 和 life_years
    返回：
        DataFrame 包含 baseline 列
    """
    # 定义基线表逻辑（基于图片数据）
    def get_baseline(scale, years):
        if pd.isna(scale) or pd.isna(years):
            return 0.0
        scale = float(scale)
        years = int(years)
        if years <= 3:
            if scale < 2:
                return 0.020
            elif 2 <= scale < 10:
                return 0.015
            else:
                return 0.008
        elif 4 <= years <= 10:
            if scale < 2:
                return 0.029
            elif 2 <= scale < 10:
                return 0.016
            else:
                return 0.009
        else:  # years > 10
            if scale < 2:
                return 0.040
            elif 2 <= scale < 10:
                return 0.020
            else:
                return 0.012

    # 获取基线值
    df['baseline'] = df.apply(lambda row: get_baseline(row['operation_scale'], row['life_years']), axis=1)
    # df['baseline'] = df['baseline'] / 100  # 转换为小数（例如 0.016% -> 0.00016）

    return df


# 整合到 main 函数
def main(p1, p2):
    # 获取参数
    year = Variable('Variable').get('BudYear')
    # year = p2.get('Year_wb1', 2025)
    # entity = p2.get('Entity_wb1', 'BEWG_Medium')

    # 初始化 cube
    cube = FinancialCube('WS_cube',path='/01_Cube')

    # 从 entity_zt_new 表获取运营驻场时间
    sql_obj = DataTableMySQL('Entity_ZT_NEW', path='/05_Datatable/05_02_Middle_Table/')
    t = sql_obj.table
    where = (t.Years_in_service.notnull())
    df_zt = sql_obj.select(columns=['sub_factory_code', 'Years_in_service'],where=where)

    # 从 cube 取出子水厂的运营规模
    fix = (
        "Account{YW0201}->Year{%s}->Scenario{Budget}->Entity{AndFilter(Descendant(1,0),Attr(ud10,'P05'))}->"
        "Measure{Nomeasure}->Period{Noperiod}->"
        "Version{Y1}->Material{Nomaterial}->Department{Operation}->"
        "Allocation{Original}->Tax{Tax}->Misc1{Nomisc1}->"
        "Misc2{Nomisc2}"
    ) %(year)
    cube_data = cube.query(expression=fix,compact=False)
    if cube_data.empty:
        print(f"警告：{year} 年份的cube运营规模数据为空")
        return
    df_cube = cube_data.rename(columns={'data': 'operation_scale'})  # 假设 value 是运营规模

    # 去重并计算运营年限
    df_zt = calculate_life_years(df_zt)

    df = pd.merge(df_cube,df_zt, on='Entity', how='left')

    # 计算基线
    df = calculate_baseline(df)

    # 写入cube时处理科目，清除无用列
    df_final = df.drop(columns=['operation_scale', 'life_years'])
    df_final = df_final.rename(columns={'baseline': 'data'})
    df_final['Account']  = 'YW0509'
    df_final['Measure']  = 'Unit'
    df_final['Department']  = 'Totaldepartment'


    # 输出结果
    print("日常维护费基线计算结果：")
    print(df_final)

    # 写回 cube
    if not df_final.empty:
        try:
            msg = cube.save(data=df_final)
            print(f"数据写入 cube 成功：{msg}")
        except Exception as e:
            print(f"数据写入 cube 失败：{e}")

if __name__ == '__main__':
    # 示例 p2
    from common._debug import para2
    p2 = {'Year_wb1': 2025, 'Entity_wb1': 'BEWG_Medium'}
    main({}, p2)