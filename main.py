from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
from datetime import datetime
from zoneinfo import ZoneInfo

@register("jrrp", "exusiaiwei", "支持AI运势生成的人品插件", "1.4.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    def get_realtime_config(self):
        '''
        使用插件管理器的实时配置获取方式。
        这能确保你在 WebUI 点击“保存”后，插件能立刻读到新值。
        '''
        try:
            # 1. 获取插件管理器中的配置对象
            # 这里的 "jrrp" 必须与 metadata.yaml 中的 name 一致
            conf = self.context.get_config().get_plugin_config("jrrp")
            return conf if conf else {}
        except Exception as e:
            # 兼容性兜底：如果上述 API 在你的版本不可用，回退到全局路径查询
            global_cfg = self.context.get_config() or {}
            return global_cfg.get("plugins", {}).get("jrrp", {})

    @filter.command("jrrpcfg")
    async def jrrpcfg(self, event: AstrMessageEvent):
        '''查询当前配置状态'''
        cfg = self.get_realtime_config()
        # 强制转换类型，防止从配置读到的是 None
        use_ai = bool(cfg.get("use_ai_description", False))
        is_weighted = bool(cfg.get("weighted_random", True))
        
        reply = (
            "🔧 实时配置同步测试：\n"
            f"AI 动态生成: {'开启 🟢' if use_ai else '关闭 🔴'}\n"
            f"高分加权算法: {'开启 🟢' if is_weighted else '关闭 🔴'}\n"
            "Tip: 如果状态仍不对，请尝试在 WebUI 点击插件页面的“重载”按钮。"
        )
        yield event.plain_result(reply)

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent):
        '''今日人品值查询'''
        user_name = event.get_sender_name()
        
        # 获取最新的实时配置
        config = self.get_realtime_config()
        is_weighted = bool(config.get("weighted_random", True))
        use_ai = bool(config.get("use_ai_description", False))

        # 计算人品值
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

        # ====== AI 生成逻辑 (参考 ai.md 推荐写法) ======
        if use_ai:
            try:
                # 获取当前会话的 provider_id
                provider_id = await self.context.get_current_chat_provider_id(event.unified_msg_origin)
                
                prompt = (
                    f"用户 {user_name} 今天的幸运值（jrrp）是 {rp}/100。"
                    "请根据分值给出一段简短、有趣、充满个性的运势点评。50字内。"
                )
                
                # 调用大模型生成
                llm_resp = await self.context.llm_generate(
                    chat_provider_id=provider_id,
                    prompt=prompt
                )
                
                if llm_resp and llm_resp.completion_text:
                    yield event.plain_result(f"{user_name}，你今天的人品是 {rp}！\n{llm_resp.completion_text}")
                    return
            except Exception as e:
                logger.error(f"[jrrp] AI 生成异常: {e}")

        # ====== 静态兜底逻辑 ======
        descriptions = [
            (10, "desc_1", "人品已欠费停机，建议今天就躺平吧！🥲"),
            (30, "desc_2", "普通的一天，像白开水一样平淡无奇~"),
            (60, "desc_3", "运气不错哦，可以试试抽卡或者告白什么的！✨"),
            (80, "desc_4", "今日锦鲤附体！适合做重要决定和冒险！🐟"),
            (100, "desc_5", "欧皇降临！今天你就是天选之人，无敌了！👑"),
        ]
        
        message_str = "运势神秘莫测..."
        for threshold, key, default in descriptions:
            if rp <= threshold:
                message_str = config.get(key, default)
                break

        yield event.plain_result(f"{user_name}，你今天的人品是{rp}，{message_str}")

    async def terminate(self):
        pass
