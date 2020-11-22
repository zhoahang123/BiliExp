from BiliClient import asyncbili
import logging

async def group_sign_task(biliapi: asyncbili) -> None:
    '''应援团签到'''
    try:
        ret = await biliapi.getMyGroups()
    except Exception as e:
        logging.warning(f'{biliapi.name}: 获取应援团信息异常，原因为{str(e)}，跳过应援团签到')
        return
    if ret["code"] != 0:
        logging.info(f'{biliapi.name}: 获取应援团信息失败，信息为:{ret["message"]}，跳过应援团签到')
        return

    for group in ret["data"]["list"]:
        try:
            sign = await biliapi.groupSign(group["group_id"], group["owner_uid"])
        except Exception as e:
            logging.warning(f'{biliapi.name}: 给{group["group_name"]}应援异常，原因为{str(e)}')
        else:
            if ret["code"] == 0:
                logging.info(f'{biliapi.name}: 给{group["group_name"]}应援成功')
            else:
                logging.info(f'{biliapi.name}: 给{group["group_name"]}应援失败，原因为:{ret["message"]}')