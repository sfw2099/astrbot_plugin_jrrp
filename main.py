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
        '''安全提取本插件专属配置的辅助函数'''
        global_config = self.context.get_config() or {}
        # 常见位置 1：直接以插件名作为 key
        if "astrbot_plugin_jrrp" in global_config:
            return global_config["astrbot_plugin_jrrp"]
        # 常见位置 2：放在 plugins 字典下
        if "plugins" in global_config and "astrbot_plugin_jrrp" in global_config["plugins"]:
            return global_config["plugins"]["astrbot_plugin_jrrp"]
        
        logger.warning("[jrrp] 未在全局配置中找到专属配置节点，将使用默认参数。")
        return {}

    @filter.command("jrrpcfg")
    async def jrrpcfg(self, event: AstrMessageEvent):
        '''查询当前配置状态，防止事件穿透给主 AI'''
        cfg = self.get_plugin_config()
        use_ai = cfg.get("use_ai_description", False)
        is_weighted = cfg.get("weighted_random", True)
        
        reply = (
            "🔧 当前 JRRP 配置状态：\n"
            f"AI 动态生成: {'开启 🟢' if use_ai else '关闭 🔴'}\n"
            f"高分加权算法: {'开启 🟢' if is_weighted else '关闭 🔴'}"
        )
        # 必须 yield 才能向用户发送消息，并阻止主 AI 继续处理
        yield event.plain_result(reply)

    @filter.command("jrrp")
    async def jrrp(self, event: AstrMessageEvent):
        '''今日人品值查询'''
        user_name = event.get_sender_name()
        
        # 使用辅助函数获取配置
        config = self.get_plugin_config()
        is_weighted = config.get("weighted_random", True)
        use_ai = config.get("use_ai_description", False)

        # 保持原有的日期种子逻辑
        utc_8 = datetime.now(ZoneInfo("Asia/Shanghai"))
        date_str = utc_8.strftime("/%y/%m%d")
        userseed = hash(date_str + user_name)
        random.seed(userseed)

        # 计算人品值
        if is_weighted:
            weights = [1, 3, 3, 1]
            ranges = [(1, 20), (21, 50), (51, 80), (81, 100)]
            selected_range = random.choices(ranges, weights=weights, k=1)[0]
            rp = random.randint(selected_range[0], selected_range[1])
        else:
            rp = random.randint(1, 100)

        # 核心：判断是否使用 AI 生成
        if use_ai:
            provider = self.context.get_using_provider()
            if provider:
                # 构造注入人格的系统提示词
                prompt = (
                    f"用户 {user_name} 今天的“人品值”（幸运值）抽到了 {rp}（满分100）。"
                    "请严格遵守你当前的角色设定和语气，用生动有趣的话告诉他今天的运势如何。字数控制在60字以内。"
                )
                try:
                    # 调用当前全局生效的大模型 Provider
                    response = await provider.text_chat(prompt)
                    ai_reply = response.text
                    yield event.plain_result(f"{user_name}，你今天的人品是 {rp}！\n{ai_reply}")
                    return # 成功后直接返回，结束函数
                except Exception as e:
                    logger.error(f"[jrrp] 请求 AI 失败，回退到静态配置文案: {e}")
            else:
                logger.warning("[jrrp] 未获取到可用的 AI Provider，回退到静态配置文案。")

        # 静态文案兜底逻辑 (如果 AI 关闭或调用失败)
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
