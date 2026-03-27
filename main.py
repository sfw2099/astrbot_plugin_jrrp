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
    async def jrrp(self, event: AstrMessageEvent = None):
        '''今日人品值查询'''
        logger.info(f"[jrrp] 开始处理命令，event: {event}")
        
        if event is None:
            yield "无法获取事件信息"
            return
        
        user_name = event.get_sender_name()
        config = self.context.get_config() or {}
        is_weighted = config.get("weighted_random", True)
        use_ai = config.get("use_ai_description", False)
        
        logger.info(f"[jrrp] 用户名: {user_name}, 配置: {config}")
        logger.info(f"[jrrp] use_ai配置值: {use_ai}, 类型: {type(use_ai)}")
        
        # 生成人品值逻辑...
        rp = 31  # 测试用固定值
        
        if use_ai:
            logger.info(f"[jrrp] AI功能已启用，准备调用AI")
            try:
                umo = event.unified_msg_origin
                logger.info(f"[jrrp] unified_msg_origin: {umo}")
                
                provider_id = await self.context.get_current_chat_provider_id(umo=umo)
                logger.info(f"[jrrp] 获取到provider_id: {provider_id}")
                
                if not provider_id:
                    logger.warning(f"[jrrp] 未获取到可用的AI模型提供商")
                    message_str = self._get_fallback_description(rp, config)
                else:
                    prompt = f"""用户{user_name}今天的人品值是{rp}（范围1-100）。
    请根据这个人品值生成一段有趣、个性化的今日运势解读。"""
                    
                    logger.info(f"[jrrp] 开始调用AI，prompt长度: {len(prompt)}")
                    
                    llm_resp = await self.context.llm_generate(
                        chat_provider_id=provider_id,
                        prompt=prompt,
                        max_tokens=200,
                        temperature=0.8
                    )
                    
                    message_str = llm_resp.completion_text.strip()
                    logger.info(f"[jrrp] AI生成成功: {message_str}")
                    
            except Exception as e:
                logger.error(f"[jrrp] AI调用异常: {str(e)}", exc_info=True)
                message_str = self._get_fallback_description(rp, config)
        else:
            logger.info(f"[jrrp] AI功能未启用，使用固定描述")
            message_str = self._get_fallback_description(rp, config)
        
        logger.info(f"[jrrp] 最终回复: {message_str}")
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
