from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
from datetime import datetime
from zoneinfo import ZoneInfo

@register("jrrp", "exusiaiwei", "一个支持自定义配置的人品插件（AI增强版）", "1.4.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent):
        '''今日人品值查询，每个用户每天固定，范围1-100，AI生成运势解读'''
        user_name = event.get_sender_name()
        
        # 获取配置
        config = self.context.get_config() or {}
        is_weighted = config.get("weighted_random", True)
        use_ai = config.get("use_ai_description", False)  # 新增配置：是否使用AI生成描述

        # 生成人品值（保持原有逻辑）
        utc_8 = datetime.now(ZoneInfo("Asia/Shanghai"))
        date_str = utc_8.strftime("/%y/%m%d")
        userseed = hash(date_str + user_name)
        random.seed(userseed)

        if is_weighted:
            weights = [1, 3, 3, 1]
            ranges = [(1, 20), (21, 50), (51, 80), (81, 100)]
            selected_range = random.choices(ranges, weights=weights, k=1)[0]
            rp = random.randint(selected_range[0], selected_range[1])
        else:
            rp = random.randint(1, 100)

        # 生成运势描述
        if use_ai:
            # 使用AI生成个性化运势解读
            try:
                umo = event.unified_msg_origin
                provider_id = await self.context.get_current_chat_provider_id(umo=umo)
                
                prompt = f"""用户{user_name}今天的人品值是{rp}（范围1-100）。
请根据这个人品值生成一段有趣、个性化的今日运势解读。
要求：
1. 语气活泼亲切，带点幽默感
2. 针对{rp}这个具体数值给出相应建议
3. 包含1-2个具体的今日小贴士
4. 用中文回复，长度在50-100字左右"""
                
                llm_resp = await self.context.llm_generate(
                    chat_provider_id=provider_id,
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.8
                )
                
                message_str = llm_resp.completion_text.strip()
                logger.info(f"AI生成运势描述成功：{message_str}")
                
            except Exception as e:
                logger.error(f"AI生成运势描述失败：{e}")
                # 失败时回退到固定描述
                message_str = self._get_fallback_description(rp, config)
        else:
            # 使用固定描述
            message_str = self._get_fallback_description(rp, config)

        yield event.plain_result(f"{user_name}，你今天的人品是{rp}，{message_str}")

    def _get_fallback_description(self, rp: int, config: dict) -> str:
        """获取固定描述（原逻辑）"""
        if 1 <= rp <= 10:
            return config.get("desc_1", "人品已欠费停机，建议今天就躺平吧！🥲")
        elif 11 <= rp <= 30:
            return config.get("desc_2", "普通的一天，像白开水一样平淡无奇~")
        elif 31 <= rp <= 60:
            return config.get("desc_3", "运气不错哦，可以试试抽卡或者告白什么的！✨")
        elif 61 <= rp <= 80:
            return config.get("desc_4", "今日锦鲤附体！适合做重要决定和冒险！🐟")
        elif 81 <= rp <= 100:
            return config.get("desc_5", "欧皇降临！今天你就是天选之人，无敌了！👑")
        return "今天的运势未知，请自行判断！"

    async def terminate(self):
        pass
