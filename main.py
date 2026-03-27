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
        # 初始化配置缓存
        self.plugin_config = {}
        # 尝试加载配置但不强制
        self._try_load_config()
    
    def _try_load_config(self):
        """尝试加载配置，但不抛出异常"""
        try:
            # 主方法：从context.get_config()获取
            all_config = self.context.get_config() or {}
            logger.info(f"[jrrp] 完整配置键(前10个): {list(all_config.keys())[:10]}")
            
            # 搜索所有可能包含插件配置的位置
            possible_locations = []
            
            # 1. 直接查找插件ID作为键
            if "jrrp" in all_config:
                self.plugin_config = all_config["jrrp"]
                logger.info(f"[jrrp] 找到配置在 all_config['jrrp']: {self.plugin_config}")
                return
            
            # 2. 查找包含"jrrp"的键
            for key in all_config:
                if "jrrp" in str(key).lower():
                    value = all_config[key]
                    if isinstance(value, dict):
                        self.plugin_config = value
                        logger.info(f"[jrrp] 找到配置在 all_config['{key}']: {self.plugin_config}")
                        return
                    else:
                        possible_locations.append(f"{key}: {value}")
            
            # 3. 查找包含"plugin"的键
            for key in all_config:
                if "plugin" in str(key).lower() and isinstance(all_config[key], dict):
                    if "jrrp" in all_config[key]:
                        self.plugin_config = all_config[key]["jrrp"]
                        logger.info(f"[jrrp] 找到配置在 all_config['{key}']['jrrp']: {self.plugin_config}")
                        return
            
            logger.info(f"[jrrp] 未找到插件专属配置，可能的位置: {possible_locations[:5]}")
            
        except Exception as e:
            logger.warning(f"[jrrp] 配置加载尝试失败(非致命): {e}")
    
    def _get_config_value(self, key: str, default=None):
        """安全获取配置值，带详细日志"""
        value = self.plugin_config.get(key, default)
        logger.info(f"[jrrp] 读取配置 {key} = {value} (类型: {type(value)})")
        return value
    
    @filter.command("jrrpcfg")
    async def show_config(self, event: AstrMessageEvent):
        '''显示当前插件配置 - 使用更独特的命令名'''
        # 重新尝试加载配置
        self._try_load_config()
        
        use_ai = self._get_config_value("use_ai_description", False)
        is_weighted = self._get_config_value("weighted_random", True)
        
        # 检查AI提供商
        umo = event.unified_msg_origin
        provider_id = await self.context.get_current_chat_provider_id(umo=umo)
        
        info = f"""🔧 jrrp插件状态检查：
• AI运势解读配置: {"✅ 已启用" if use_ai else "❌ 未启用"}
• 高分加权配置: {"✅ 已启用" if is_weighted else "❌ 未启用"}
• 可用AI提供商: {provider_id or "（需在AstrBot全局配置中启用）"}
• 当前插件配置: {self.plugin_config or "空"}

💡 如果AI未启用，请检查：
1. 在AstrBot管理界面 → jrrp插件 → 配置
2. 确保"启用AI运势解读"开关为蓝色/开启状态
3. 点击保存按钮
4. 重新发送本命令查看最新状态"""
        
        yield info

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent = None):
        '''今日人品值查询'''
        logger.info(f"[jrrp] 收到/jrrp命令")
        
        if event is None:
            yield "无法获取事件信息"
            return
        
        # 每次执行都重新尝试加载配置
        self._try_load_config()
        
        user_name = event.get_sender_name()
        
        # 从可能的位置获取AI配置
        use_ai = self._get_config_value("use_ai_description", False)
        is_weighted = self._get_config_value("weighted_random", True)
        
        logger.info(f"[jrrp] 用户:{user_name}, AI配置值:{use_ai}, 加权配置值:{is_weighted}")
        
        # 生成人品值
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
            logger.info(f"[jrrp] 根据配置尝试调用AI...")
            try:
                umo = event.unified_msg_origin
                provider_id = await self.context.get_current_chat_provider_id(umo=umo)
                
                if not provider_id:
                    message_str = self._get_fallback_description(rp)
                    logger.warning(f"[jrrp] AI已配置但无可用提供商，使用固定描述")
                else:
                    # 构造请求AI的提示词
                    prompt = f"""用户"{user_name}"的今日人品值（随机生成，范围1-100）为：{rp}。
请根据此数值，生成一段简短、有趣、幽默的"今日运势"解读。用中文回答，长度控制在100字以内。"""
                    
                    logger.info(f"[jrrp] 正在调用AI模型: {provider_id}")
                    llm_resp = await self.context.llm_generate(
                        chat_provider_id=provider_id,
                        prompt=prompt,
                        max_tokens=150,
                        temperature=0.8
                    )
                    
                    message_str = llm_resp.completion_text.strip()
                    logger.info(f"[jrrp] AI生成成功")
                    
            except Exception as e:
                logger.error(f"[jrrp] AI调用异常: {e}")
                message_str = self._get_fallback_description(rp)
        else:
            message_str = self._get_fallback_description(rp)
            logger.info(f"[jrrp] AI配置未启用，使用固定描述")
        
        yield event.plain_result(f"{user_name}，你今天的人品值是{rp}！{message_str}")

    def _get_fallback_description(self, rp: int) -> str:
        """固定描述后备"""
        if 1 <= rp <= 10:
            return "人品已欠费停机，建议今天就躺平吧！🥲"
        elif 11 <= rp <= 30:
            return "普通的一天，像白开水一样平淡无奇~"
        elif 31 <= rp <= 60:
            return "运气不错哦，可以试试抽卡或者告白什么的！✨"
        elif 61 <= rp <= 80:
            return "今日锦鲤附体！适合做重要决定和冒险！🐟"
        elif 81 <= rp <= 100:
            return "欧皇降临！今天你就是天选之人，无敌了！👑"
        return "今天的运势未知，请自行判断！"

    async def terminate(self):
        logger.info("[jrrp] 插件终止")
