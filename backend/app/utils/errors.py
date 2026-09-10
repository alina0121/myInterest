"""统一响应包络与业务错误码（对应 docs/04-接口文档.md §0.5）。

码段约定：1xxx 鉴权/参数，2xxx 用户，3xxx 持仓，4xxx 批次/分红，
5xxx 预案，9xxx 服务端。前端可按码段做不同的提示与跳转。
所有业务错误一律 raise AppError，由 main.py 的异常处理器统一包成 JSON。
"""


class Codes:
    OK = 0
    VALIDATION = 1001        # 参数校验失败 (422)
    UNAUTHORIZED = 1002      # 未登录 (401)
    TOKEN_INVALID = 1003     # token 过期或无效 (401)
    FORBIDDEN = 1004         # 无权限 (403)
    NOT_FOUND = 1005         # 资源不存在或不属于当前用户 (404)
    BAD_CREDENTIALS = 2001   # 用户名或密码错误 (401)
    USER_EXISTS = 2002       # 用户名/邮箱已存在 (409)
    HOLDING_EXISTS = 3001    # 该标的持仓已存在 (409)
    NEGATIVE_SHARES = 4001   # 卖出后持仓数量为负 (400)
    NO_ELIGIBLE = 4002       # 登记日无符合条件持仓，无法生成分红 (400)
    SCHEDULE_DUPLICATE = 5001  # 预案重复 (409)
    SERVER_ERROR = 9000      # 服务器内部错误 (500)


class AppError(Exception):
    def __init__(self, code: int, msg: str, status: int = 400):
        self.code = code
        self.msg = msg
        self.status = status
        super().__init__(msg)


def not_found(msg: str = "记录不存在或已被删除") -> AppError:
    return AppError(Codes.NOT_FOUND, msg, status=404)


def ok(data=None) -> dict:
    """成功响应包络。列表空数据返回 []，金额无数据返回 0。"""
    return {"code": Codes.OK, "msg": "ok", "data": data}
