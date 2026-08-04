from deepfos.element import FinancialCube, DataTableMySQL,Dimension
from deepfos.element.variable import Variable
import pandas as pd
import numpy as np
from fin_bizvoucher_cube_old import main as old_main


def get_data():
    """获取数据并处理维度，过滤无效数据（核心：确保project_cd在Spec_Proj_td中存在）"""

    print("===== 开始获取并处理数据 =====")

    # 1.1 获取fin_bizvoucher_item_info原始数据
    fin_dt = DataTableMySQL("spec_Amount_info")
    cols = [
        "year_code", "period_code", "spec_proj_code",
        # "spec_proj_type_code",
        "localamt"
    ]
    fin_df = fin_dt.select(columns=cols).rename(columns={
        "spec_proj_code":"Entity_Sp",
        # "spec_proj_type_code":"Spec_Proj",
        "year_code":"Year",
        "period_code":"Period_code",
        # "manage_subj_code":"Profit_acct",
        "localamt":"data",
    })


    #
    # 在建工程AT1005、固定资产AT1001、无形资产AT1009,取借方金额
    # 累计折旧AT9999,取贷方金额
    # 其余的取发生额


    # 2.0 获取Entity_Sp_td原始数据
    Entity_dt = DataTableMySQL("Entity_Sp_td")
    cols = [
        "name", "ud4"
    ]
    Entity_df = Entity_dt.select(columns=cols,where = "ud6 != '停用'").rename(columns={
        "name": "Entity_Sp",
        "ud4": "Spec_Proj",
    })


    fin_df = pd.merge(
        fin_df,
        Entity_df,
        on="Entity_Sp",
        how="inner"
    )

    # 2.1 获取Spec_Proj_td原始数据
    Spec_dt = DataTableMySQL("Spec_Proj_td")
    cols = [
        "name", "ud1"
    ]
    Spec_df = Spec_dt.select(columns=cols).rename(columns={
        "name": "Spec_Proj",
        "ud1": "Department",
    })

    # 2.2 根据专项项目类型编码匹配主责中心
    df = pd.merge(
        fin_df,
        Spec_df,
        on="Spec_Proj",
        how="left"
    )

    # 2.3 主责中心匹配不上的 修改为D_99
    df['Department'] = df['Department'].fillna("D_99")


    # 匹配Entity_Sp
    # entity_dt = Dimension('Entity_Sp')
    # entity_df = pd.DataFrame(entity_dt.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    # valid_entities = entity_df['name'].tolist()  # 或 .unique().tolist()
    # # 过滤掉不在维度中的项目
    # df = df[df['Entity_Sp'].isin(valid_entities)]
    # 过滤掉不在维度中的项目
    return df


def filter_df(p2,df):
    # year = Variable('Variable').get('Year')



    df['Profit_acct']='Expence'

    # df.drop('Confirm_Status', axis=1, inplace=True)

    df['Spec_Proj'] = df['Spec_Proj'].fillna('No_MISC')

    df['Scenario'] = 'Actual'
    df['Version'] = 'workversion'
    df['Contract'] = 'NoContract'
    df['Misc1'] = 'NoMisc1'
    df['Misc2'] = 'NoMisc2'
    df['Misc3'] = 'NoMisc3'


    # 汇总金额
    key_cols = df.columns.drop('data').tolist()

    df = df.groupby(key_cols, as_index=False)['data'].sum()

    cube = FinancialCube("Sp_XM")
    del_pov = {
        "Department":"Base(D_all,0)",
        "Scenario":"Actual",
        "Version":"workversion",
        "Contract":"NoContract",
        "Misc1":"NoMisc1",
        "Misc2":"NoMisc2",
        "Misc3":"NoMisc3",
        "Year": p2['Year_wb1'],
        "Period_code": "Base(TotalPeriod,0)",
        "Spec_Proj": "IDescendant(SP_02,0)",
        "Entity_Sp": "IDescendant(#root,0)",
        "Profit_acct":["Expence"],

    }
    cube.delete(del_pov)
    cube.save(df)




def main(p1, p2):
    p2 = {'Year_wb1': '2025',}
    result_df = get_data()

    if result_df.empty:
        print("===== 无有效数据，终止流程 =====")
        return

    filter_df(p2,result_df)
    old_main(p1,p2)


if __name__ == "__main__":

    from ZX.__debug import para1, para2  # 假设调试参数正确导入
    para2 = {'Year_wb1': '2025',}
    main(para1, para2)
