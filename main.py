from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
from datetime import datetime
from zoneinfo import ZoneInfo

@register("jrrp", "exusiaiwei", "支持AI运势生成的人品插件", "1.4.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    def get_plugin_config(self):
        """
        核心修复：安全提取插件专属配置。
        AstrBot 将插件配置存储在全局配置的 plugins 节点下，键名为 metadata.yaml 中的 name。
        """
        global_config = self.context.get_config() or {}
        plugins_cfg = global_config.get("plugins", {})
        
        # 对应 metadata.yaml 中的 name: jrrp
        plugin_name = "jrrp" 
        
        if plugin_name in plugins_cfg:
            return plugins_cfg[plugin_name]
        
        # 兼容性处理：尝试匹配 ID 格式
        elif "astrbot_plugin_jrrp" in plugins_cfg:
            return plugins_cfg["astrbot_plugin_jrrp"]
            
        return {}

    @filter.command("jrrpcfg")
    async def jrrpcfg(self, event: AstrMessageEvent):
        '''查询当前配置状态，验证配置是否生效'''
        cfg = self.get_plugin_config()
        # 注意：这里从配置中取值，若取不到则使用代码默认值
        use_ai = cfg.get("use_ai_description", False)
        is_weighted = cfg.get("weighted_random", True)
        
        reply = (
            "🔧 当前 JRRP 内部读取到的配置：\n"
            f"AI 动态生成: {'开启 🟢' if use_ai else '关闭 🔴'}\n"
            f"高分加权算法: {'开启 🟢' if is_weighted else '关闭 🔴'}"
        )
        yield event.plain_result(reply)

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent):
        '''今日人品值查询'''
        user_name = event.get_sender_name()
        
        # 获取实时配置
        config = self.get_plugin_config()
        is_weighted = config.get("weighted_random", True)
        use_ai = config.get("use_ai_description", False)

        # 1. 计算人品值 (保持原有逻辑)
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

        # 2. AI 动态生成逻辑
        if use_ai:
            try:
                # 使用推荐的新版 LLM 调用方式
                provider_id = await self.context.get_current_chat_provider_id(event.unified_msg_origin)
                prompt = (
                    f"用户 {user_name} 今天的“人品值”是 {rp}（满分100）。"
                    "请根据这个分数，用生动幽默且符合你人格设定的语气写一段运势简评。字数50字以内。"
                )
                
                llm_resp = await self.context.llm_generate(
                    chat_provider_id=provider_id,
                    prompt=prompt
                )
                
                ai_reply = llm_resp.completion_text
                yield event.plain_result(f"{user_name}，你今天的人品是 {rp}！\n{ai_reply}")
                return 
            except Exception as e:
                logger.error(f"[jrrp] AI 生成失败: {e}")

        # 3. 静态文案兜底逻辑
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
