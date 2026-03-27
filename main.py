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
    async def jrrp(self, event: AstrMessageEvent):
        '''今日人品值查询，每个用户每天固定，范围1-100'''
        user_name = event.get_sender_name()
        
        # 从 _conf_schema.json 加载配置
        config = self.context.get_config()
        weighted_random = config.get("weighted_random", True)
        fortune_levels = config.get("fortune_levels", [])

        # 保持原有的日期种子逻辑
        utc_8 = datetime.now(ZoneInfo("Asia/Shanghai"))
        date_str = utc_8.strftime("/%y/%m%d")
        userseed = hash(date_str + user_name)
        random.seed(userseed)

        # 计算人品值
        if weighted_random:
            # 保持原有的加权区间逻辑
            weights = [1, 3, 3, 1]
            ranges = [(1, 20), (21, 50), (51, 80), (81, 100)]
            selected_range = random.choices(ranges, weights=weights, k=1)[0]
            rp = random.randint(selected_range[0], selected_range[1])
        else:
            rp = random.randint(1, 100)

        # 从配置中查找对应的描述
        message_str = "今天的运势未知，请自行判断！"
        for level in fortune_levels:
            if level["min"] <= rp <= level["max"]:
                message_str = level["desc"]
                break

        yield event.plain_result(f"{user_name}，你今天的人品是{rp}，{message_str}")

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
