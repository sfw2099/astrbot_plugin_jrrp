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
        # 初始化时尝试加载配置
        self._load_config()
    
    def _load_config(self):
        """从AstrBot配置系统加载插件配置"""
        try:
            # 方法1：使用AstrBot的标准配置获取方式
            config = self.context.get_config_manager().get_plugin_config("jrrp")
            if config:
                logger.info(f"[jrrp] 通过get_plugin_config获取配置: {config}")
                self.plugin_config = config
                return
            
            # 方法2：尝试从全局配置中查找
            all_config = self.context.get_config() or {}
            logger.info(f"[jrrp] 完整配置键: {list(all_config.keys())}")
            
            # 在全局配置中搜索jrrp相关配置
            for key in all_config:
                if "jrrp" in key.lower():
                    logger.info(f"[jrrp] 找到相关配置键: {key} = {all_config[key]}")
                    if isinstance(all_config[key], dict):
                        self.plugin_config = all_config[key]
                        return
            
            # 方法3：尝试获取配置管理器中的插件配置
            try:
                config_manager = getattr(self.context, "config_manager", None)
                if config_manager:
                    plugin_config = config_manager.get("jrrp", {})
                    if plugin_config:
                        self.plugin_config = plugin_config
                        logger.info(f"[jrrp] 通过config_manager获取配置: {plugin_config}")
                        return
            except:
                pass
                
            # 方法4：直接尝试从context的属性中获取
            for attr in dir(self.context):
                if "config" in attr.lower() or "setting" in attr.lower():
                    try:
                        value = getattr(self.context, attr)
                        if isinstance(value, dict) and "jrrp" in value:
                            self.plugin_config = value.get("jrrp", {})
                            logger.info(f"[jrrp] 从context.{attr}获取配置")
                            return
                    except:
                        continue
            
            logger.warning("[jrrp] 无法找到插件配置，使用默认配置")
            self.plugin_config = {}
            
        except Exception as e:
            logger.error(f"[jrrp] 加载配置失败: {e}")
            self.plugin_config = {}
    
    def _get_config_value(self, key: str, default=None):
        """安全获取配置值"""
        return self.plugin_config.get(key, default)
    
    @filter.command("jrrpinfo")
    async def show_config(self, event: AstrMessageEvent):
        '''显示当前插件配置 - 使用独特的命令名'''
        # 重新加载配置以确保获取最新值
        self._load_config()
        
        use_ai = self._get_config_value("use_ai_description", False)
        is_weighted = self._get_config_value("weighted_random", True)
        
        # 检查AI提供商
        umo = event.unified_msg_origin
        provider_id = await self.context.get_current_chat_provider_id(umo=umo)
        
        # 显示完整配置用于调试
        config_info = "\n".join([f"  - {k}: {v}" for k, v in self.plugin_config.items()])
        
        info = f"""🔧 jrrp插件配置详情：
• AI运势解读: {"✅已启用" if use_ai else "❌未启用"}
• 高分加权: {"✅已启用" if is_weighted else "❌未启用"}
• AI提供商: {provider_id or "未配置"}
• 所有配置项:
{config_info if config_info else "  无配置信息"}"""
        
        yield info

    @filter.command("testconfig")
    async def test_config(self, event: AstrMessageEvent):
        '''测试配置读取'''
        # 获取完整的上下文信息
        all_config = self.context.get_config() or {}
        
        # 列出所有可能的配置位置
        config_locations = []
        for key, value in all_config.items():
            if isinstance(value, dict):
                config_locations.append(f"{key} (dict)")
            else:
                config_locations.append(f"{key}: {value}")
        
        yield f"📋 配置位置测试:\n" + "\n".join(config_locations[:20])  # 只显示前20个

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent = None):
        '''今日人品值查询'''
        if event is None:
            yield "无法获取事件信息"
            return
        
        # 重新加载配置以确保获取最新值
        self._load_config()
        
        user_name = event.get_sender_name()
        use_ai = self._get_config_value("use_ai_description", False)
        is_weighted = self._get_config_value("weighted_random", True)
        
        logger.info(f"[jrrp] 用户:{user_name}, AI启用:{use_ai}, 加权:{is_weighted}, 配置:{self.plugin_config}")
        
        # 如果配置为空，强制显示配置信息
        if not self.plugin_config:
            yield f"{user_name}，插件配置加载异常，请检查AstrBot配置界面是否已保存配置。发送 /jrrpinfo 查看详情。"
            return
        
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
        
        # AI生成或固定描述
        if use_ai:
            logger.info(f"[jrrp] AI功能已启用，尝试调用...")
            try:
                umo = event.unified_msg_origin
                provider_id = await self.context.get_current_chat_provider_id(umo=umo)
                
                if not provider_id:
                    message_str = self._get_fallback_description(rp)
                    logger.warning("[jrrp] 无可用AI提供商，使用固定描述")
                else:
                    prompt = f"""用户{user_name}今日人品值：{rp}/100。请生成一段有趣、个性化的运势解读，包含具体建议，用中文回复，100字内。"""
                    
                    llm_resp = await self.context.llm_generate(
                        chat_provider_id=provider_id,
                        prompt=prompt,
                        max_tokens=150,
                        temperature=0.7
                    )
                    
                    message_str = llm_resp.completion_text.strip()
                    logger.info(f"[jrrp] AI生成成功: {message_str[:50]}...")
                    
            except Exception as e:
                logger.error(f"[jrrp] AI调用失败: {e}")
                message_str = self._get_fallback_description(rp)
        else:
            message_str = self._get_fallback_description(rp)
            logger.info(f"[jrrp] AI未启用，使用固定描述")
        
        yield event.plain_result(f"{user_name}，今日人品：{rp}，{message_str}")

    def _get_fallback_description(self, rp: int) -> str:
        """固定描述后备"""
        # 使用硬编码的描述，不依赖配置
        if 1 <= rp <= 10:
            return "人品欠费，建议躺平！🥲"
        elif 11 <= rp <= 30:
            return "平凡的一天~"
        elif 31 <= rp <= 60:
            return "运气不错，适合尝试！✨"
        elif 61 <= rp <= 80:
            return "锦鲤附体，勇敢冒险！🐟"
        elif 81 <= rp <= 100:
            return "欧皇降临，无敌！👑"
        return "运势未知~"

    async def terminate(self):
        logger.info("[jrrp] 插件终止")
