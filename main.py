from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
from datetime import datetime
from zoneinfo import ZoneInfo

@register("jrrp", "exusiaiwei", "一个支持自定义配置的人品插件", "1.3.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent = None):
        '''今日人品值查询，每个用户每天固定，范围1-100'''
        if event is None:
            # 处理event为空的情况，例如直接返回一个结果
            yield "无法获取事件信息"
            return
        user_name = event.get_sender_name()
        
        # 获取配置，若无则使用默认值
        config = self.context.get_config() or {}
        is_weighted = config.get("weighted_random", True)

        # 保持原有的日期种子逻辑
        utc_8 = datetime.now(ZoneInfo("Asia/Shanghai"))
        date_str = utc_8.strftime("/%y/%m%d")
        userseed = hash(date_str + user_name)
        random.seed(userseed)

        # 保持原有的计算逻辑
        if is_weighted:
            weights = [1, 3, 3, 1]
            ranges = [(1, 20), (21, 50), (51, 80), (81, 100)]
            selected_range = random.choices(ranges, weights=weights, k=1)[0]
            rp = random.randint(selected_range[0], selected_range[1])
        else:
            rp = random.randint(1, 100)

        # 匹配描述项
        # 这里的范围映射逻辑与你 README 中的定义保持一致
        message_str = "今天的运势未知，请自行判断！"
        if 1 <= rp <= 10:
            message_str = config.get("desc_1", "人品已欠费停机，建议今天就躺平吧！🥲")
        elif 11 <= rp <= 30:
            message_str = config.get("desc_2", "普通的一天，像白开水一样平淡无奇~")
        elif 31 <= rp <= 60:
            message_str = config.get("desc_3", "运气不错哦，可以试试抽卡或者告白什么的！✨")
        elif 61 <= rp <= 80:
            message_str = config.get("desc_4", "今日锦鲤附体！适合做重要决定和冒险！🐟")
        elif 81 <= rp <= 100:
            message_str = config.get("desc_5", "欧皇降临！今天你就是天选之人，无敌了！👑")

        yield event.plain_result(f"{user_name}，你今天的人品是{rp}，{message_str}")

    async def terminate(self):
        pass
