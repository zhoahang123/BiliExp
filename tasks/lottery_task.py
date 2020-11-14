from BiliClient import asyncbili
from .import_once import now_time
from random import randint
import logging, json, asyncio, re

end_time = now_time - (now_time + 28800) % 86400 + 43200 #当天中午12点
start_time = end_time - 86400

async def lottery_task(biliapi: asyncbili, 
                       task_config: dict    #配置
                       ) -> None:
    
    already_repost_dyid = set() #记录动态列表中自己已经转发的动态id
    rexs = [re.compile(x, re.S) for x in task_config["keywords"]]
    
    try:
        async for x in get_dynamic(biliapi):
            if x["desc"]["uid"] == biliapi.uid and x["desc"]["pre_dy_id_str"] != '0':
                already_repost_dyid.add(int(x["desc"]["pre_dy_id_str"]))
                continue
            
            timestamp = x["desc"]["timestamp"]
            if(timestamp > end_time):
                continue
            elif(timestamp < start_time):
                break

            if 'card' in x:
                card = json.loads(x["card"])
                if 'item' in card:
                    if 'description' in card["item"]:
                        text = card["item"]["description"]
                    elif 'content' in card["item"]:
                        text = card["item"]["content"]
                    else:
                        text = None
                    if text:
                        flag = False
                        for rex in rexs:
                            if re.match(rex, text):
                                flag = True
                                if "uname" in x["desc"]["user_profile"]["info"]:
                                    uname = x["desc"]["user_profile"]["info"]["uname"]
                                elif "name" in x["desc"]["user_profile"]["info"]:
                                    uname = x["desc"]["user_profile"]["info"]["name"]
                                else:
                                    uname = '未知用户'
                                dyid = x["desc"]["dynamic_id"]
                                if dyid in already_repost_dyid: #若动态被转发过就跳过
                                    continue
                                
                                if isinstance(task_config["repost"], list):
                                    if len(task_config["repost"]) > 0:
                                        repost: str = task_config["repost"][randint(0, len(task_config["repost"]) - 1)] #取随机评论
                                    else:
                                        repost: str = ''
                                else:
                                    repost: str = task_config["repost"]

                                if isinstance(task_config["reply"], list):
                                    if len(task_config["reply"]) > 0:
                                        reply: str = task_config["reply"][randint(0, len(task_config["reply"]) - 1)]
                                    else:
                                        reply: str = ''
                                else:
                                    reply: str = task_config["reply"]

                                if x["desc"]["pre_dy_id"]:
                                    oid, type = dyid, 17      #如果当前动态是转发的，评论id就是oid，评论类型为17
                                elif "id" in card["item"]:    #当前动态不是转发的，评论id就是item id，评论类型为11
                                    oid, type = card["item"]["id"], 11
                                elif "rp_id" in card["item"]: #后面两种情况一般没用
                                    oid, type = card["item"]["rp_id"], 11
                                else:
                                    oid, type = dyid, 11

                                try:
                                    ret = await biliapi.dynamicReplyAdd(oid, reply, type)
                                except Exception as e: 
                                    logging.warning(f'{biliapi.name}: 评论关键字动态(用户名:{uname},动态id:{dyid})失败，原因为({str(e)})')
                                else:
                                    if ret["code"] == 0:
                                        logging.info(f'{biliapi.name}: 评论关键字动态(用户名:{uname},动态id:{dyid})成功')
                                    else:
                                        logging.warning(f'{biliapi.name}: 评论关键字动态(用户名:{uname},动态id:{dyid})失败，信息为{ret["message"]}')

                                retry = task_config.get("retry", [3, 20])
                                times = 0
                                while retry[0] >= times and not await dynamicRepost(biliapi, dyid, repost, "关键字", uname):
                                    times += 1
                                    await asyncio.sleep(retry[1])

                                break

                        if flag:
                            if "delay" in task_config:
                                await asyncio.sleep(randint(task_config["delay"][0], task_config["delay"][1]))
                            else:
                                await asyncio.sleep(3)
                            continue

            if 'extension' in x and 'lott' in x["extension"]: #若抽奖标签存在
                if "uname" in x["desc"]["user_profile"]["info"]:
                    uname = x["desc"]["user_profile"]["info"]["uname"]
                elif "name" in x["desc"]["user_profile"]["info"]:
                    uname = x["desc"]["user_profile"]["info"]["name"]
                else:
                    uname = '未知用户'
                dyid = x["desc"]["dynamic_id"]
                if dyid in already_repost_dyid: #若动态被转发过就跳过
                    continue

                if isinstance(task_config["repost"], list):
                    if len(task_config["repost"]) > 0:
                        repost: str = task_config["repost"][randint(0, len(task_config["repost"]) - 1)] #取随机评论
                    else:
                        repost: str = ''
                else:
                    repost: str = task_config["repost"]

                if isinstance(task_config["reply"], list):
                    if len(task_config["reply"]) > 0:
                        reply: str = task_config["reply"][randint(0, len(task_config["reply"]) - 1)]
                    else:
                        reply: str = ''
                else:
                    reply: str = task_config["reply"]

                if 'card' in x:
                    card = json.loads(x["card"])
                    if "id" in card["item"]:
                        oid, type = card["item"]["id"], 11  #一般会执行到这里，其他取值情况几乎不存在
                    elif "rp_id" in card["item"]:
                        oid, type = card["item"]["rp_id"], 17
                    else:
                        oid, type = dyid, 17
                else:
                    oid, type = dyid, 17

                try:
                    ret = await biliapi.dynamicReplyAdd(oid, reply, type)
                except Exception as e: 
                    logging.warning(f'{biliapi.name}: 评论抽奖动态(用户名:{uname},动态id:{dyid})失败，原因为({str(e)})')
                else:
                    if ret["code"] == 0:
                        logging.info(f'{biliapi.name}: 评论抽奖动态(用户名:{uname},动态id:{dyid})成功')
                    else:
                        logging.warning(f'{biliapi.name}: 评论抽奖动态(用户名:{uname},动态id:{dyid})失败，信息为{ret["message"]}')


                retry = task_config.get("retry", [3, 20])
                times = 0
                while retry[0] >= times and not await dynamicRepost(biliapi, dyid, repost, "抽奖", uname):
                    times += 1
                    await asyncio.sleep(retry[1])

                if "delay" in task_config:
                    await asyncio.sleep(randint(task_config["delay"][0], task_config["delay"][1]))
                else:
                    await asyncio.sleep(3)

    except Exception as e: 
        logging.warning(f'{biliapi.name}: 获取动态列表异常，原因为{str(e)}，跳过转发抽奖动态')
        return

async def get_dynamic(biliapi: asyncbili) -> dict:
    '''取B站用户动态数据，异步生成器'''
    offset = 0
    hasnext = True
    retry = 3 #连续失败重试次数
    while hasnext:
        try:
            ret = await biliapi.getDynamic(offset)
        except Exception as e: 
            if retry:
                retry -= 1
                logging.warning(f'{biliapi.name}: 获取动态列表异常，原因为{str(e)}，重试动态列表获取')
            else:
                logging.warning(f'{biliapi.name}: 获取动态列表异常，原因为{str(e)}，跳过获取')
                break
        else:
            retry = 3
            if ret["code"] == 0:
                if "has_more" in ret["data"]:
                    hasnext = (ret["data"]["has_more"] == 1)
                cards = ret["data"]["cards"]
                if not len(cards):
                    break
                offset = cards[-1]["desc"]["dynamic_id"]
                for x in cards:
                    yield x
            else:
                logging.warning(f'{biliapi.name}: 获取动态列表失败，原因为{ret["msg"]}，跳过转发抽奖动态')
                break

async def dynamicRepost(biliapi: asyncbili,
                        dyid: int,
                        repost: str,
                        type: str,
                        uname: str
                        ):
    '''转发B站动态'''
    repostOK = False
    try:
        ret = await biliapi.dynamicRepostReply(dyid, repost)
    except Exception as e: 
        repostMsg = str(e)
    else:
        if ret["code"] == 0:
            logging.info(f'{biliapi.name}: 转发{type}动态(用户名:{uname},动态id:{dyid})成功')
            repostOK = True
        else:
            repostMsg = ret["message"]

    if not repostOK:
        try:
            ret = await biliapi.dynamicRepost(dyid, repost)
        except Exception as e: 
            logging.warning(f'{biliapi.name}: (评论)转发{type}动态(用户名:{uname},动态id:{dyid})失败，信息为{repostMsg}，独立转发异常，信息为({str(e)})')
        else:
            if ret["code"] == 0:
                logging.info(f'{biliapi.name}: (评论)转发{type}动态(用户名:{uname},动态id:{dyid})失败，信息为{repostMsg}，但是独立转发成功')
                repostOK = True
            else:
                logging.warning(f'{biliapi.name}: (评论)转发{type}动态(用户名:{uname},动态id:{dyid})失败，信息为{repostMsg}，独立转发仍然失败，信息为{ret["message"]}')

    if ret["code"] == 1101008:
        return repostOK
    return True