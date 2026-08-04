from deepfos.options import OPTION

# -----------------------------------------------------------------------------
# 从系统中获取以下参数
#: 环境参数
# para1 = {'app': 'yhacsq010', 'space': 'yhacsq', 'user': '9e3d21a3-bda3-4d9c-9a70-a7ae562ba184', 'language': 'zh-cn', 'token': 'F75B30BC6E2A6B57192C0A4F2796D2934348298A22345106D7F08F63306CC81C', 'cookie': 'OAUTH2SESSION=NjA4MzUyYTYtZjJiMy00MDFlLWJlZWQtMWRkODIzOTkyMWQ1; deepfos_users=%7B%22email%22%3A%22%22%2C%22invitationActivation%22%3Atrue%2C%22nickName%22%3A%22%E7%8E%8B%E6%94%BF%22%2C%22nickname%22%3A%22%E7%8E%8B%E6%94%BF%22%2C%22token%22%3A%22F75B30BC6E2A6B57192C0A4F2796D2934348298A22345106D7F08F63306CC81C%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%229e3d21a3-bda3-4d9c-9a70-a7ae562ba184%22%2C%22username%22%3A%22v-wangzheng%22%7D; deepfos_token=F75B30BC6E2A6B57192C0A4F2796D2934348298A22345106D7F08F63306CC81C', 'Content-Type': 'application/json;charset=UTF8'}
para1 = {'app': 'yhacsq015', 'space': 'yhacsq', 'user': '41cba8da-cf06-4b4d-8104-46e9900ea0e5', 'language': 'zh-cn', 'token': 'C820CCAEE16E5B1B3E6A4B5558A422BAEEBA1DB120BE5E5546A78A969A0E1E86', 'cookie': 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22mobilePhone%22%3A%2213671042437%22%2C%22nickName%22%3A%22%E9%99%88%E6%99%B6%E7%A3%8A%22%2C%22nickname%22%3A%22%E9%99%88%E6%99%B6%E7%A3%8A%22%2C%22token%22%3A%22C820CCAEE16E5B1B3E6A4B5558A422BAEEBA1DB120BE5E5546A78A969A0E1E86%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%2241cba8da-cf06-4b4d-8104-46e9900ea0e5%22%2C%22username%22%3A%22w-chenjinglei01%22%7D; deepfos_token=C820CCAEE16E5B1B3E6A4B5558A422BAEEBA1DB120BE5E5546A78A969A0E1E86; iam_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsib2F1dGgyLXJlc291cmNlIl0sInVzZXJfbmFtZSI6InctY2hlbmppbmdsZWkwMSIsInNjb3BlIjpbImFsbCJdLCJyb2xlcyI6W10sImV4cCI6MTc1NzYwMjIwMCwicmVzb3VyY2VfaWRzIjpbIm9hdXRoMi1yZXNvdXJjZSJdLCJ1c2VySWQiOiJ3LWNoZW5qaW5nbGVpMDEiLCJqdGkiOiJiMWMwMDA5NS0yMjZhLTRlYWEtOTFmYi0yMGE1NzBkZTVmZTMiLCJjbGllbnRfaWQiOiJpYW1fdG9vbDIiLCJ1c2VybmFtZSI6InctY2hlbmppbmdsZWkwMSJ9.IZkQrEy6pWidzwj3XXAwOIJYzzHOkhQZAKPc_wTGiqa0O_3lHUFIuy1WcX8eRt_PQYvlADVxEeFi4OJhMg7QSC6Xi9-1wvEDC52mxdwLLn9HgI-Q9kk6vHAWZY1T9oe-mBs6qD4jbaXdKsc4WmyfMMmQEvGbS78AXjwpQuftNXewNMJRogvEXgYDgl2WKybXjPUL2ed69WAi-2l6TBybowlYvzlKiMXQ52QLhHvayWaXgG6s5cuFBm-cBtSEzunYxlaVxBKhN3OydQjMHPYZzpETEV3TdPTXiJHmvQEyDDRy5g__h3-vzsXQkQXEY2C2HtMfOtp33SnYS6psM7hnjg', 'envUrl': 'http://web-gateway'}


#: 业务参数
para2 = {'currentStatus': 'Status587e', 'operationTime': '2021-07-27 14:48:53', 'operationUser': '1fff29c5-abdc-4929-ab6c-8a6ca9479091', 'pcRemark': '', 'primaryKeyValue': {'partition_id': 'SUBEEB6VDKAO0I', 'sub_id': '1', 'sys_store_id': 'fran_store0003'}, 'targetStatus': 'Statusa600'}

#: 环境域名，根据自己的使用环境更改
# host = "https://alpha.deepfos.com"
host = "https://budget-uat.bewg.net.cn"



# -----------------------------------------------------------------------------
# 下面的代码是固定的

OPTION.general.use_eureka = False
OPTION.server.base = f"{host}/seepln-server"
OPTION.server.app = f"{host}/seepln-server/app-server"
OPTION.server.system = f"{host}/seepln-server/system-server"
OPTION.server.space = f"{host}/seepln-server/space-server"
OPTION.server.platform_file = f"{host}/seepln-server/platform-file-server"
OPTION.api.header = para1
OPTION.api.dump_on_failure = True