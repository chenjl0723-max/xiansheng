try:
    from CWYS.__debug import para1#, para2
except ImportError:
    #para1 = para2 = {}
    print('~~~')
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.pyscript import PythonScript
import pandas as pd
import time,os
from datetime import datetime,timedelta

def dim_fullSave(result,v_dimPath,v_dimName,v_reorder):
    #全量数据进行增量更新
    try:
        result.reset_index(inplace=True,drop=True)
        # 检查是否存在名为 'index' 的列，如果存在则删除
        if 'index' in result.columns:
            result.drop(columns=['index'], inplace=True)
        # 添加新的 'index' 列
        result['index'] = range(len(result))
    except Exception as e:
        print(f"尝试全量更新错误：生成维度index字段出现错误:{e}")
        raise ValueError(f"尝试全量更新错误：生成维度index字段出现错误:{e}")
    try:
        dim = Dimension(element_name=v_dimName, path=v_dimPath)
        a = dim.load_dataframe(dataframe=result, strategy='incr_replace',reorder=v_reorder, language_zh_cn='description_zh_cn', language_en='description_en')
    except Exception as e:
        print(f"尝试全量更新错误：更新维度出现错误:{e}")
        raise ValueError(f"尝试全量更新错误：更新维度对象出现错误:{e}")
    msg=f"全量{'排序' if v_reorder else '不排序'}更新完成"
    return msg

def dim_save(v_dt,v_tablePath,v_dimPath,v_dimName,v_dimTableName):
    msg=''
    print(f"更新{v_dimPath}-{v_dimName},路径:{v_tablePath}-{v_dimTableName}")
    try:
        table=DataTableMySQL(element_name=v_dimTableName)
        result = table.select().drop(['_id','aggweight','sharedmember','is_active'], axis=1).rename(columns={"parentName": "parent_name"})

        print(f"本次获取数据量：{result.shape[0]}")
        msg+=f"本次获取数据量：{result.shape[0]}"
        # dim = Dimension(element_name=v_dimName, path=v_dimPath)
        # # 按照层级不排序更新
        # a = dim.load_dataframe(dataframe=result, strategy='full_replace', reorder=False,
        #                        language_zh_cn='description_zh_cn', language_en='description_en')

        if len(result)==0:
            raise ValueError(f"数据量为0，请检查数据！")
    except Exception as e:
        print(f"获取维度数据出现错误:{e}")
        raise ValueError(f"获取维度数据出现错误:{e}")
    #按照层级更新维度
    try:
        # result['index'] = result.groupby('level').cumcount() #dimension API Index字段说明：排序，指该节点在同一个父节点下的排序，从0开始 原始值：parent_name
        if 'index' in result.columns:
            result.drop(columns=['index'], inplace=True)
        # 添加新的 'index' 列
        result['index'] = range(len(result))
    except Exception as e:
        print(f"生成维度index字段出现错误:{e}")
        raise ValueError(f"生成维度index字段出现错误:{e}")
    resultLevelList = sorted(result['entity_level'].unique())
    print(resultLevelList)
    for level in resultLevelList:
        print(f"更新层级{level}")
        level_data = result[result['entity_level'] == level]
        try:
            dim = Dimension(element_name=v_dimName, path=v_dimPath)
            # 按照层级不排序更新
            a = dim.load_dataframe(dataframe=level_data, strategy='incr_replace',reorder=False, language_zh_cn='description_zh_cn', language_en='description_en')
        except Exception as e:
            print(f"更新维度层级{level}出现错误:{str(e)[:300]}")
            if '父级节点不存在' in str(e):
                print("更新失败原因为父级不存在，取消全量重试")
                msg+=f"更新失败原因为父级不存在，取消全量重试\n"
                raise ValueError(f"更新失败原因为父级不存在，取消全量重试")
            else:
                # msg+=f"当前层级{level}更新出现错误，尝试单个循环更新\n"
                # level_data_code=level_data['name'].unique()
                # level_data_code_sum=level_data_code.shape[0]
                # level_data_code_num=0
                # for name in level_data_code:
                #     level_data_code_num+=1
                #     oneCodeDf=level_data[level_data['name']==name]
                #     print(f"更新组织{name}({level_data_code_num}/level_data_code_sum)")
                #     try:
                #         a = dim.load_dataframe(dataframe=oneCodeDf, strategy='incr_replace',reorder=False, language_zh_cn='description_zh_cn', language_en='description_en')
                #     except Exception as e:
                #         raise ValueError(f"更新单个组织{name}出错!{e}")

                # 定义每次处理的name数量
                n = 5
                msg += f"当前层级{level}更新出现错误，尝试每{n}个循环更新一次\n"
                level_data_code = level_data['name'].unique()
                level_data_code_sum = level_data_code.shape[0]

                

                # 每次循环处理n个name
                for i in range(0, level_data_code_sum, n):
                    names_to_process = level_data_code[i:i+n]  # 获取当前循环的n个name
                    combined_df = level_data[level_data['name'].isin(names_to_process)]  # 合并n个name的数据
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 更新{level}层组织{', '.join(names_to_process)} ({i//n + 1}/{(level_data_code_sum + n - 1) //                 n})")
                    try:
                        a = dim.load_dataframe(
                            dataframe=combined_df,
                            strategy='incr_replace',
                            reorder=False,
                            language_zh_cn='description_zh_cn',
                            language_en='description_en'
                        )
                    except Exception as e:
                        print(f"更新组织{', '.join(names_to_process)}出错!尝试单个更新！{str(e)[:300]}")
                        for j in range(len(combined_df)):
                            rowDf=combined_df.iloc[[j]]
                            print(f"更新单个组织{rowDf.iloc[0]['name']}")
                            try:
                                a = dim.load_dataframe(
                                    dataframe=rowDf,
                                    strategy='incr_replace',
                                    reorder=False,
                                    language_zh_cn='description_zh_cn',
                                    language_en='description_en'
                                )
                            except Exception as e:
                                raise ValueError(f"更新组织{rowDf.iloc[0]['name']}出错! {str(e)[:300]}")




                # msg += f"当前层级{level}更新出现错误，尝试每两个循环更新一次\n"
                # level_data_code = level_data['name'].unique()
                # level_data_code_sum = level_data_code.shape[0]
                
                # # 每次循环处理两个 name
                # for i in range(0, level_data_code_sum, 2):
                #     names_to_process = level_data_code[i:i+2]  # 获取当前循环的两个 name
                #     combined_df = level_data[level_data['name'].isin(names_to_process)]  # 合并两个 name 的数据
                #     print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}更新{level}层组织{', '.join(names_to_process)} ({i//2 + 1}/{(level_data_code_sum + 1) // 2})")
                #     try:
                #         a = dim.load_dataframe(
                #             dataframe=combined_df,
                #             strategy='incr_replace',
                #             reorder=False,
                #             language_zh_cn='description_zh_cn',
                #             language_en='description_en'
                #         )
                #     except Exception as e:
                #         raise ValueError(f"更新组织{', '.join(names_to_process)}出错! {e}")



            #     msg+=f"按照层级更新出现错误，尝试全量更新\n"
            #     try:
            #         print(f"尝试全量不排序更新{v_dimPath}-{v_dimName}")
            #         msg+=dim_fullSave(result=result,v_dimName=v_dimName,v_dimPath=v_dimPath,v_reorder=False)
            #     except Exception as e:
            #         msg+=f"尝试全量不排序更新错误"
            #         print(f"尝试全量不排序更新错误：{e}")
            #         raise ValueError(f"尝试全量不排序更新错误：{e}")
            # break
    #全量排序更新
    # try:
    #     print(f"尝试全量排序更新{v_dimPath}-{v_dimName}")
    #     msg+=dim_fullSave(result=result,v_dimName=v_dimName,v_dimPath=v_dimPath,v_reorder=True)
    # except Exception as e:
    #     msg+=f"尝试全量排序更新错误"
    #     print(f"尝试全量排序更新错误：{str(e)[:300]}")
    #     raise ValueError(f"尝试全量排序更新错误")
    # print('完成')
    # return msg


def main(p1, p2):
    #获取当天日期
    now = datetime.now()
    v_dt = now.strftime('%Y%m%d');

    
    dimTablePath='/05_Datatable/05_99_public/'
    dimPath='/02_Dimension/'
    dimDicList={
        'Entity_GL':{'dimPath':dimPath,'tablePath':dimTablePath,'tableName':'ZT_Entity'},
        'Entity_FR':{'dimPath':dimPath,'tablePath':dimTablePath,'tableName':'ZT_Entity_FR'},
    }

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll=0
    countSuccess=0
    countError=0
    countMsg=''
    if p2 and 'dim' in p2:
        dim_names = p2['dim'].split(';')
        countAll=len(dim_names)
        countMsg+=f"{start_time}共需要更新{countAll}个维度\n"
        for dim_name in dim_names:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if dim_name in dimDicList:
                value = dimDicList[dim_name]
                try:
                    exe=dim_save(v_dt=v_dt,v_tablePath=value['tablePath'], v_dimPath=value['dimPath'], v_dimName=dim_name, v_dimTableName=value['tableName'])
                    countSuccess+=1
                    countMsg+=f"{current_time}更新{dim_name}维度成功{exe}\n"
                except Exception as e:
                    countError+=1
                    countMsg+=f"{current_time}更新{dim_name}-{value}维度出现错误\n"
                    print(f"更新{dim_name}-{value}维度出现错误:{e}")
            else:
                countError+=1
                countMsg+=f"{current_time}指定的维度 {dim_name} 不在 dimDicList 中\n"
                print(f"指定的维度 {dim_name} 不在 dimDicList 中")
            print()
    else:
        countAll=len(dimDicList)
        countMsg+=f"{start_time}共需要更新{countAll}个维度\n"
        for key, value in dimDicList.items():
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            try:
                exe=dim_save(v_dt=v_dt,v_tablePath=value['tablePath'], v_dimPath=value['dimPath'], v_dimName=key, v_dimTableName=value['tableName'])
                countSuccess+=1
                countMsg+=f"{current_time}更新{key}-{value}维度出现成功{exe}\n"
            except Exception as e:
                countError+=1
                countMsg+=f"{current_time}更新{key}-{value}维度出现错误\n"
                print(f"更新{key}-{value}维度出现错误:{e}")
        print()
    #记录日志###############################################################
    # 获取调用此函数的模块的文件名和路径
    # caller_frame = inspect.stack()[1]
    # caller_module = inspect.getmodule(caller_frame[0])
    # caller_filename = caller_module.__file__
    ele_name=os.path.basename(__file__)
    ele_path=os.path.dirname(os.path.abspath(__file__))
    sync_log=PythonScript(element_name='pyLog', path='/09_Python/common',should_log=True)
    sync_result=sync_log.run(
        parameter={
            'ele_name':ele_name,
            'ele_path':ele_path,
            'data_count': countAll,
            'error_count': countError,
            'logs': countMsg,
            'dt': v_dt,
            'start_time': start_time,
            'exe_parameter':str(p2)
        }
    )
    if sync_result: 
        print("日志记录成功！")
    else:
        print("日志记录失败！")
    if countError>0:
        return False
    else:
        return True

    


if __name__ == '__main__':
    # p2={'dim':'entity_test2','dt':'20241126'}
    p2={"dim":"Entity_FR"}
    main(para1, p2)
