"""语料筛选用的规则：哪些话是用户真说的、哪些像在做裁决。

只做机械判断，不做语义理解——语义留给后面的抽取环节。
正则针对中文对话调过；英文会话命中率低，需要时自行扩充。
"""
import re

# Claude 确实在征询：只看消息末尾，且要求真问句或明确交球
RE_ASK_TAIL = re.compile(
    r'([？?]\s*$|[？?]["」』）)]*\s*$|'
    r'(倾向哪|选哪|哪一?个|要不要|是否要|你定|你说了算|你来定|等你|你拍板|'
    r'确认后我|要我(去|来|先)?|需要我|同意吗|可以吗|行吗|对吗|好吗|怎么弄|怎么办))')

# 纯反应词（不含「改成 / 加 / 删」等自发需求动词）
RE_REACT = re.compile(
    r'(不对|不用了|别[这那再]|错了|不是这[样个]|重来|回退|撤销|为什么(不|要)|'
    r'算了|没必要|过度|多余|谁让你|我没说|你误解|跑偏|不行|停[一下]?$|'
    r'同意|可以[，。,.]|OK|ok|好的|就[用走这那]|用第|选[第这那123一二三ABab]|'
    r'方案[一二三ABab123]|按你说的|按你的|听你的|你定|够了|足够|保持|不需要改|对，|是的|没错)')

# 协作元反馈：用户在规定 Claude 的工作方式
RE_META = re.compile(
    # 立规矩 / 泛化到未来
    r'(以后|下次|每次|一律|默认(就|都|请|用|走)|今后|往后|从现在起|记住|别忘|'
    r'原则上|我的(习惯|偏好|风格|要求|规矩)|我喜欢|我讨厌|我反感|我不喜欢|'
    r'写进?\s*CLAUDE|记到|记一下|沉淀|加进规则|定个规矩|'
    # 直接评价 Claude 的工作方式
    r'你(应该|要|得|别|不要|不用|怎么老|怎么总|为什么老|为什么总)|'
    r'你自己(定|判断|决定|看着办|拿主意)|自己拿主意|你来定就行|'
    r'不要(每次|老是|总是|反复|再)|别(每次|老是|总是|反复|问我|再问|啰嗦)|'
    r'这还用问|不用问我|问我干嘛|我不想(每次|再|又)|'
    # 沟通风格反馈
    r'太(啰嗦|长|细|碎|啰唆|多了)|说重点|别废话|说人话|简洁|精简|直接(给|说|做|上)|'
    r'我说过|我不是说|刚才(不是)?说|前面说过|重复(问|说))')

# 强纠正：history 源没有 Claude 上文兜底，所以比 RE_REACT 严，「OK」「可以」这类弱信号在那里是噪音
RE_STRONG_FIX = re.compile(
    r'(不对|错了|不是这[样个]|重来|回退|撤销|为什么(不|要|没|还)|谁让你|我没说|你误解|'
    r'跑偏|不行啊?|算了|没必要|过度|多余|又出|还是(有问题|不行|没)|怎么(还|又|老|总)|'
    r'你没有?|漏了|丢了|忘了|白做|返工|推翻|重做)')

# history 源的噪音：slash 命令、纯确认、裸路径 / URL
RE_NOISE = re.compile(
    r'^(/|!|#|\s*$|(ok|OK|好的?|嗯+|继续|是的?|对|行|可以|谢谢|thx|y|n|yes|no)[\s。.!！]*$)')
RE_BARE_PATH = re.compile(r'^\s*(https?://\S+|[/~][\w\-./ ]+)\s*$')

# 系统注入文本以 user 身份出现在日志里，但不是用户的话——混进去会污染「用户原话」这一核心证据
INJECTED_PREFIX = (
    "<system-reminder", "<command-", "<local-command", "<user-prompt-submit",
    "Caveat:", "[Request interrupted", "Base directory for this skill",
    "This session is being continued", "<summary>", "Summary:", "# Skill:",
    "Analysis:", "The user sent the following message", "<task-notification",
    "Your questions have been answered", "The user answered:",
)
INJECTED_ANY = re.compile(
    r'(This session is being continued from a previous conversation|'
    r'Base directory for this skill:|'
    r'covers the earlier portion of the conversation)')


def text_of(content):
    """把消息 content（字符串或 block 列表）拼成纯文本，只取 text block。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return ""


def strip_noise(s):
    """去掉夹在用户消息里的系统提醒、本地命令输出，图片占位统一成 [图]。"""
    s = re.sub(r'<system-reminder>.*?</system-reminder>', '', s, flags=re.S)
    s = re.sub(r'<local-command-[^>]*>.*?</local-command-[^>]*>', '', s, flags=re.S)
    s = re.sub(r'\[Image[^\]]*\]', '[图]', s)
    return s.strip()


def is_real_user_text(s):
    """非空，且不是以 user 身份注入的系统文本。注入文本有时前面挂了一小段，所以扫开头 400 字。"""
    s = s.strip()
    if not s or s.startswith(INJECTED_PREFIX):
        return False
    return not INJECTED_ANY.search(s[:400])


def usable_history_input(s):
    """history.jsonl 里值得进语料的输入：够长、不是命令 / 纯确认 / 裸路径、不是注入文本。"""
    s = s.strip()
    if len(s) < 8 or RE_NOISE.match(s) or RE_BARE_PATH.match(s):
        return False
    return is_real_user_text(s)
