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
        logger.info("[jrrp] 插件初始化完成")

    def _get_plugin_config(self):
        """
        安全地获取本插件的配置字典。
        AstrBot中，插件配置可能存储在全局配置的以插件ID（'jrrp'）为键的子字典中。
        """
        # 1. 获取完整配置
        all_config = self.context.get_config() or {}
        
        # 2. 优先尝试从插件ID键下获取配置（这是AstrBot常见存储方式）
        plugin_config = all_config.get("jrrp", {})
        
        # 3. 如果上述方式未找到，尝试直接从根配置中查找（备用逻辑）
        if not plugin_config and "use_ai_description" in all_config:
            # 如果配置是扁平化的，则直接使用根配置
            plugin_config = all_config
            logger.info("[jrrp] 配置模式：扁平化根配置")
        else:
            logger.info(f"[jrrp] 配置模式：嵌套配置 (jrrp: {plugin_config})")
        
        return plugin_config

    @filter.command("rpconfig")
    async def show_config(self, event: AstrMessageEvent):
        '''显示当前插件配置 - 使用更独特的命令名'''
        plugin_config = self._get_plugin_config()
        
        # 从正确的配置位置读取值
        use_ai = plugin_config.get("use_ai_description", False)
        is_weighted = plugin_config.get("weighted_random", True)
        
        # 检查AI提供商是否可用
        umo = event.unified_msg_origin
        provider_id = await self.context.get_current_chat_provider_id(umo=umo)
        
        info = f"""🔧 jrrp插件当前配置：
• 启用AI运势解读: **{"✅ 是" if use_ai else "❌ 否"}**
• 启用高分加权: **{"✅ 是" if is_weighted else "❌ 否"}**
• 可用AI提供商: {provider_id or "（未配置或全局未启用）"}"""
        
        yield info

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent = None):
        '''今日人品值查询'''
        logger.info(f"[jrrp] 开始处理命令")
        
        if event is None:
            yield "无法获取事件信息"
            return
        
        user_name = event.get_sender_name()
        
        # 使用修正后的方法获取配置
        plugin_config = self._get_plugin_config()
        use_ai = plugin_config.get("use_ai_description", False)
        is_weighted = plugin_config.get("weighted_random", True)
        
        logger.info(f"[jrrp] 用户:{user_name}, AI启用状态:{use_ai}, 加权状态:{is_weighted}")
        
        # 生成基于日期的确定性随机人品值
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
        
        logger.info(f"[jrrp] 生成人品值: {rp}")
        
        # 根据配置决定使用AI生成还是固定描述
        if use_ai:
            logger.info(f"[jrrp] AI功能已启用，尝试调用...")
            try:
                umo = event.unified_msg_origin
                provider_id = await self.context.get_current_chat_provider_id(umo=umo)
                
                if not provider_id:
                    message_str = self._get_fallback_description(rp, plugin_config)
                    logger.warning(f"[jrrp] 无可用AI提供商，已回退到固定描述。")
                else:
                    # 构造请求AI的提示词
                    prompt = f"""用户“{user_name}”的今日人品值（随机生成，范围1-100）为：{rp}。
请根据此数值，生成一段简短、有趣、幽默的“今日运势”解读。用中文回答，长度控制在100字以内。"""
                    
                    logger.info(f"[jrrp] 调用AI模型: {provider_id}")
                    llm_resp = await self.context.llm_generate(
                        chat_provider_id=provider_id,
                        prompt=prompt,
                        max_tokens=150,
                        temperature=0.8
                    )
                    
                    message_str = llm_resp.completion_text.strip()
                    logger.info(f"[jrrp] AI生成成功，内容: {message_str[:50]}...")
                    
            except Exception as e:
                logger.error(f"[jrrp] AI调用过程中发生异常: {e}", exc_info=True)
                message_str = self._get_fallback_description(rp, plugin_config)
        else:
            message_str = self._get_fallback_description(rp, plugin_config)
            logger.info(f"[jrrp] AI功能未启用，使用固定描述。")
        
        yield event.plain_result(f"{user_name}，你今天的人品值是{rp}！{message_str}")

    def _get_fallback_description(self, rp: int, config: dict) -> str:
        """当AI未启用或调用失败时使用的固定描述后备"""
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
        logger.info("[jrrp] 插件终止")
