from BiliClient import asyncbili
import logging, asyncio, uuid, time, aiohttp

async def xlive_heartbeat_task(biliapi: asyncbili,
                               task_config: dict
                               ) -> None:

    num: int = task_config.get("num", 0)
    if not num:
        return

    room_id: int = task_config.get("room_id", 0)
    if not room_id:
        level = intimacy = 0
        try:
            ret = await biliapi.get_home_medals()
            if ret["code"] == 0 and ret["data"]["cnt"] > 0:
                for x in ret["data"]["list"]:
                    if x["level"] > level or (x["level"] == level and x["intimacy"] > intimacy):
                        accinfo = await biliapi.accInfo(x["target_id"])
                        if accinfo["code"] == 0 and accinfo["data"]["live_room"]["liveStatus"] == 1:
                            room_id = accinfo["data"]["live_room"]["roomid"]
                            level = x["level"]
                            intimacy = x["intimacy"]
            else:
                logging.info(f'{biliapi.name}: 获取直播间失败，跳过直播心跳。(建议手动指定直播间)')
                return
        except Exception as e:
            logging.info(f'{biliapi.name}: 获取直播间异常，原因为{str(e)}，跳过直播心跳。(建议手动指定直播间)')
            return

        if not room_id:
            logging.info(f'{biliapi.name}: 没有领取过勋章且在线的直播间，跳过直播心跳。(建议手动指定直播间)')
            return

    try:
        ret = await biliapi.xliveGetRoomInfo(room_id)
        if ret["code"] != 0:
            logging.info(f'{biliapi.name}: 直播请求房间信息失败，信息为：{ret["message"]}，跳过直播心跳')
            return
        parent_area_id = ret["data"]["room_info"]["parent_area_id"]
        area_id = ret["data"]["room_info"]["area_id"]
        room_id = ret["data"]["room_info"]["room_id"] #为了防止上面的id是短id，这里确保得到的是长id
    except Exception as e:
        logging.warning(f'{biliapi.name}: 直播请求房间信息异常，原因为{str(e)}，跳过直播心跳')
        return

    try:
        buvid = await biliapi.xliveGetBuvid()
    except Exception as e:
        logging.warning(f'{biliapi.name}: 获取直播buvid异常，原因为{str(e)}，跳过直播心跳')
        return

    ii = 0
    try:
        async for code, message, wtime in xliveHeartBeat(biliapi, buvid, parent_area_id, area_id, room_id): #每一次迭代发送一次心跳
            if code != 0:
                logging.warning(f'{biliapi.name}: 直播心跳错误，原因为{message}，跳过直播心跳')
                return
            ii += 1
            if ii < num:
                logging.info(f'{biliapi.name}: 成功在id为{room_id}的直播间发送第{ii}次心跳')
                await asyncio.sleep(wtime) #等待wtime秒进行下一次迭代
            else:
                logging.info(f'{biliapi.name}: 成功在id为{room_id}的直播间发送完{ii}次心跳，退出直播心跳')
                break
            
    except Exception as e:
        logging.warning(f'{biliapi.name}: 直播心跳异常，原因为{str(e)}，退出直播心跳')
        return

class xliveHeartBeat:
    '''B站心跳异步迭代器，每迭代一次发送一次心跳'''

    def __init__(self, biliapi: asyncbili, buvid: str, parent_area_id: int, area_id: int, room_id: int):
        self._biliapi = biliapi
        self._data = {
            "id": [parent_area_id, area_id, 0, room_id],
            "device": [buvid, str(uuid.uuid4())]
            }
        self._secret_rule: list = None

    async def _encParam(self) -> str:
        '''加密参数'''
        url = 'http://116.85.43.27:3000/enc'
        #url = 'http://www.madliar.com:6000/enc' #备用地址
        async with aiohttp.request("post", url=url, json={"t":self._data, "r":self._secret_rule}) as r:
            ret = await r.json()
        return ret["s"]

    def __aiter__(self):
        return self

    async def __anext__(self):
        
        if self._data["id"][2] == 0:   #第1次执行进入房间心跳 HeartBeatE
            ret = await self._biliapi.xliveHeartBeatE(**self._data)
            if ret["code"] == 0:
                self._data["ets"] = ret["data"]["timestamp"]
                self._data["benchmark"] = ret["data"]["secret_key"]
                self._data["time"] = ret["data"]["heartbeat_interval"]
                self._secret_rule = ret["data"]["secret_rule"]
                self._data["id"][2] += 1
            return ret["code"], ret["message"], ret["data"]["heartbeat_interval"]

        else:                          #第n>1次执行进入房间心跳 HeartBeatX
            self._data["ts"] = int(time.time() * 1000)
            self._data["s"] = await self._encParam()
            ret = await self._biliapi.xliveHeartBeatX(**self._data)
            if ret["code"] == 0:
                self._data["ets"] = ret["data"]["timestamp"]
                self._data["benchmark"] = ret["data"]["secret_key"]
                self._data["time"] = ret["data"]["heartbeat_interval"]
                self._secret_rule = ret["data"]["secret_rule"]
                self._data["id"][2] += 1
            return ret["code"], ret["message"], ret["data"]["heartbeat_interval"]