from BiliClient import asyncbili
from .import_once import get_ids
import logging

async def coin_task(biliapi: asyncbili, 
                    task_config: dict
                    ) -> None:

    if biliapi.myexp >= task_config["target_exp"]:
        logging.info(f'{biliapi.name}: 已达到经验目标，跳过投币')
        return

    coin_num = biliapi.mycoin
    if coin_num == 0:
        logging.info(f'{biliapi.name}: 硬币不足，跳过投币')
        return

    try:
        reward = (await biliapi.getReward())["data"]
        #print(f'{biliapi.name}: 经验脚本开始前经验信息 ：{str(reward)}')
    except Exception as e: 
        logging.warning(f'{biliapi.name}: 获取账户经验信息异常，原因为{str(e)}，跳过投币')
        return

    coin_exp_num = (task_config["num"] * 10 - reward["coins_av"]) // 10
    toubi_num = coin_exp_num if coin_num > coin_exp_num else coin_num
    toubi_num = int(toubi_num)
    toubi_num = 1
    
    if toubi_num < 1:
        return
    else:
        try:
            async for aid, flag in get_coin_aids(biliapi, task_config):
                #flag为0，aid为视频id，flag为up主uid，aid为专栏id
                if flag:
                    try:
                        ret = await biliapi.coinCv(aid, 1, flag, 1)
                    except Exception as e:
                        logging.warning(f'{biliapi.name}: 投币专栏{aid}异常，原因为{str(e)}')
                        continue
                    else:
                        if ret["code"] == 0:
                            toubi_num -= 1
                            logging.info(f'{biliapi.name}: 成功给专栏{aid}视频投一个币')
                        elif ret["code"] == -104:
                            logging.warning(f'{biliapi.name}: 投币专栏{aid}失败，原因为{ret["message"]}，跳过投币')
                            break #这里可能硬币不够了
                        else:
                            logging.warning(f'{biliapi.name}: 投币专栏{aid}失败，原因为{ret["message"]}')
                else:
                    try:
                        ret = await biliapi.coin(aid, 1, 1)
                    except Exception as e:
                        logging.warning(f'{biliapi.name}: 投币视频av{aid}异常，原因为{str(e)}')
                        continue
                    else:
                        if ret["code"] == 0:
                            toubi_num -= 1
                            logging.info(f'{biliapi.name}: 成功给av{aid}视频投一个币')
                        elif ret["code"] == -104:
                            logging.warning(f'{biliapi.name}: 投币专栏{aid}失败，原因为{ret["message"]}，跳过投币')
                            break
                        else:
                            logging.warning(f'{biliapi.name}: 投币视频av{aid}失败，原因为{ret["message"]}')
                if not toubi_num:
                    break
        except Exception as e:
            logging.warning(f'{biliapi.name}: 获取B站视频信息异常，原因为{str(e)}，跳过投币')
            return

async def get_following_up(biliapi: asyncbili) -> int:
    '''获取关注的up主，异步迭代器'''
    pn = 1
    ret = await biliapi.getFollowings(pn=pn)
    if ret["code"]:
        logging.info(f'{biliapi.name}: 投币获取up主失败，信息为:{ret["message"]}')
        return
    pnum = ret["data"]["total"] // 50
    if ret["data"]["total"] % 50 > 0:
        pnum += 1
    while ret["data"]["list"]:
        for x in ret["data"]["list"]:
            yield x["mid"]
        pn += 1
        if pnum < pn:
            break
        ret = await biliapi.getFollowings(pn=pn)
        if ret["code"]:
            logging.info(f'{biliapi.name}: 投币获取up主失败，信息为:{ret["message"]}')
            break

async def get_up_video_ids(biliapi: asyncbili, 
                    upid: int,
                    num: int
                    ) -> int:
    '''获取指定up主的视频aid，异步迭代器'''
    if num < 1:
        return
    pn = 1
    ret = await biliapi.spaceArcSearch(uid=upid, pn=pn)
    if ret["code"]:
        logging.info(f'{biliapi.name}: 投币获取up主{upid}的视频失败，信息为:{ret["message"]}')
        return
    pnum = ret["data"]["page"]["count"] // 100
    if ret["data"]["page"]["count"] % 100 > 0:
        pnum += 1
    while ret["data"]["list"]["vlist"]:
        for x in ret["data"]["list"]["vlist"]:
            yield x["aid"]
            num -= 1
            if num < 1:
                return
        pn += 1
        if pnum < pn:
            return
        ret = await biliapi.spaceArcSearch(uid=upid, pn=pn)
        if ret["code"]:
            logging.info(f'{biliapi.name}: 投币获取up主{upid}的视频失败，信息为:{ret["message"]}')
            return

async def get_up_article_ids(biliapi: asyncbili, 
                    upid: int,
                    num: int
                    ) -> int:
    '''获取指定up主的专栏aid，异步迭代器'''
    if num < 1:
        return
    pn = 1
    ret = await biliapi.spaceArticle(uid=upid, pn=pn)
    if ret["code"]:
        logging.info(f'{biliapi.name}: 投币获取up主{upid}的视频失败，信息为:{ret["message"]}')
        return
    pnum = ret["data"]["count"] // 30
    if ret["data"]["count"] % 30 > 0:
        pnum += 1
    while ret["data"]["articles"]:
        for x in ret["data"]["articles"]:
            yield x["id"]
            num -= 1
            if num < 1:
                return
        pn += 1
        if pnum < pn:
            return
        ret = await biliapi.spaceArticle(uid=upid, pn=pn)
        if ret["code"]:
            logging.info(f'{biliapi.name}: 投币获取up主{upid}的视频失败，信息为:{ret["message"]}')
            return

async def get_coin_aids(biliapi: asyncbili, 
                    task_config: dict
                    ) -> int:
    '''按条件生成需要投币的稿件id，异步生成器'''
    if not 'mode' in task_config or task_config["mode"] == 0:
        for x in (await get_ids(biliapi))["data"]["archives"]:
            yield x["aid"], 0
    elif task_config["mode"] == 1:
        if 'up' in task_config:
            for uid in task_config["up"]:
                for cointype in task_config["coin"]:
                    if cointype == 'video':
                        async for aid in get_up_video_ids(biliapi, uid, task_config["coin"][cointype]):
                            yield aid, 0
                    elif cointype == 'article':
                        async for aid in get_up_article_ids(biliapi, uid, task_config["coin"][cointype]):
                            yield aid, uid
        else:
            async for uid in get_following_up(biliapi):
                for cointype in task_config["coin"]:
                    if cointype == 'video':
                        async for aid in get_up_video_ids(biliapi, uid, task_config["coin"][cointype]):
                            yield aid, 0
                    elif cointype == 'article':
                        async for aid in get_up_article_ids(biliapi, uid, task_config["coin"][cointype]):
                            yield aid, uid
        if 'complement' in task_config and task_config["complement"]:
            for x in (await get_ids(biliapi))["data"]["archives"]:
                yield x["aid"], 0