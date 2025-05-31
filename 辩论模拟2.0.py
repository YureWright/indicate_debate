import random
import json
from openai import OpenAI
import os
import re
import dashscope
import time
import pyaudio
import dashscope
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dashscope.audio.tts_v2 import *
from datetime import datetime
dashscope.api_key = "sk-2a75d81da0274f579e9a69715bb1050e"  # 替换为你自己的 API Key



#配置声音
def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
# dashscope.api_key = "your-api-key"

# 模型
model_voice = "cosyvoice-v2"
# 音色
voice = "longxiaochun_v2"

# 定义回调接口
class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        print("连接建立：" + get_timestamp())
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        print("语音合成完成，所有合成结果已被接收：" + get_timestamp())

    def on_error(self, message: str):
        print(f"语音合成出现异常：{message}")

    def on_close(self):
        print("连接关闭：" + get_timestamp())
        # 停止播放器
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " 二进制音频长度为：" + str(len(data)))
        self._stream.write(data)


def voice_func(text):
    callback = Callback()
    synthesizer = SpeechSynthesizer(
    model=model_voice,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=callback,
)
    synthesizer.streaming_call(text)
    time.sleep(0.1)
# 结束流式语音合成
    synthesizer.streaming_complete()



# 初始化OpenAI客户端
client = OpenAI(
    api_key="sk-2a75d81da0274f579e9a69715bb1050e",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def extract_json(content):
    # 使用正则表达式匹配JSON代码块
    json_pattern = re.compile(r'```json\s*([\s\S]*?)\s*```', re.IGNORECASE)
    match = json_pattern.search(content)
    
    if match:
        # 提取JSON内容
        json_str = match.group(1).strip()
        
        try:
            # 验证是否为有效JSON
            parsed_json = json.loads(json_str)
            return parsed_json
        except json.JSONDecodeError:
            print("提取的内容不是有效的JSON格式")
            return None
    else:
        # 尝试直接解析整个内容是否为JSON
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            print("未找到JSON代码块，且整个内容也不是JSON")
            return None



class Debater:
    def __init__(self, name, personality, style):
        self.name = name
        self.personality = personality
        self.style = style

class TeamCaptain(Debater):
    def __init__(self, name, role, personality, style, debaters):
        super().__init__(name,personality, style)
        self.debaters = debaters
        self.role=role

    def choose_speaker(self, opponent_statements, team_statements, topic):
        # 调用API来选择出战队员并解释原因
        prompt = (
    f"你是关于'{topic}'这一辩题的辩论中{self.role}方的队长。\n\n"
    f"当前辩论状态：\n"
    f"1. 对方上一轮陈述为：{opponent_statements[-1] if opponent_statements else '无'}\n"
    f"2. 你方可用辩手：{[debater.name for debater in self.debaters]}\n\n"
    f"任务：请选择一名队员进行下一轮辩论发言，并说明选择理由。\n\n"
    f"输出要求：\n"
    f"1. 严格使用以下JSON格式，不包含任何其他文本：\n"
    f'{{"chosen": "辩手姓名", "reason": "选择理由"}} \n'
    f"2. 'chosen'字段必须是你方可用辩手中的一员\n"
    f"3. 'reason'字段应具体说明选择该辩手的战术考量\n\n"
    f"示例输出：\n"
    f'{{"chosen": "张三", "reason": "对方在上一轮提出了经济模型的漏洞，而张三是我方的经济学专家，擅长数据论证"}}'
)
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": f"You are a {self.personality} and {self.style} debater on the {self.role} side."},
                {"role": "user", "content": prompt},
            ],
            extra_body={"enable_thinking": False},
        )
        json_data = response.model_dump_json()
        data_js = json.loads(json_data)
        message = data_js["choices"][0].get("message", {})
        content = message.get("content", "").strip()

        try:
            choice_dict = extract_json(content)
            chosen_name = choice_dict['chosen']
            reason = choice_dict['reason']
        except (json.JSONDecodeError, KeyError):
            chosen_name = random.choice(self.debaters).name
            reason = "无法解析JSON，随机选择"+content

        for debater in self.debaters:
            if debater.name == chosen_name:
                return debater, reason
        return random.choice(self.debaters), reason

    def decide_to_concede(self, statements, topic):
        # 调用API来决定是否认输并解释原因
        prompt = (
    f"你是关于'{topic}'这一辩题的辩论中{self.role}方的队长。\n\n"
    f"当前辩论状态：\n"
    f"1. 你方近期陈述：{statements}\n\n"
    f"任务：请决定是否认输，并说明理由。\n\n"
    f"输出要求：\n"
    f"1. 严格使用以下JSON格式，不包含任何其他文本：\n"
    f'{{"concede": true/false, "reason": "具体理由"}} \n'
    f'2. "concede"字段必须为布尔值（true或false）\n'
    f'3. "reason"字段需详细说明战术考量或认输依据\n\n'
    f"示例输出：\n"
    f'{{"concede": false, "reason": "对方虽然在某方面暂时领先，但我方第三辩手准备的新论据将扭转局势"}}'
        )
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": f"You are a {self.personality} and {self.style} debater on the {self.role} side."},
                {"role": "user", "content": prompt},
            ],
            extra_body={"enable_thinking": False},
        )
        json_data = response.model_dump_json()
        data_js = json.loads(json_data)
        message = data_js["choices"][0].get("message", {})
        content = message.get("content", "").strip()

        try:
            choice_dict = extract_json(content)
            decision = choice_dict['concede']
            reason = choice_dict['reason']
        except (json.JSONDecodeError, KeyError):
            decision = False
            reason = "无法解析JSON，默认不认输"

        return decision, reason

def get_debater_response_a(debater, topic, previous_statement):
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": f"假设你是{debater.name},你的性格为{debater.personality}，你的特点为{debater.style}，现在，你现在正在参加一场辩论赛，你的队长选择你进行出战，请根据你的身份和你的特点尽可能地对对手进行反驳或论述，你的立场是：正方."},
            {"role": "user", "content": f"The topic is: {topic}. The previous statement was: {previous_statement}. Please provide your argument."},
        ],
        extra_body={"enable_thinking": False},
    )
    json_data = completion.model_dump_json()
    data_js = json.loads(json_data)
    message = data_js["choices"][0].get("message", {})
    answer = message.get("content", "")
    return answer


def get_debater_response_b(debater, topic, previous_statement):
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": f"假设你是{debater.name},你的性格为{debater.personality}，你的特点为{debater.style}，现在，你现在正在参加一场辩论赛，你的队长选择你进行出战，请根据你的身份和你的特点尽可能地对对手进行反驳或论述，你的立场是：反方."},
            {"role": "user", "content": f"The topic is: {topic}. The previous statement was: {previous_statement}. Please provide your argument."},
        ],
        extra_body={"enable_thinking": False},
    )
    json_data = completion.model_dump_json()
    data_js = json.loads(json_data)
    message = data_js["choices"][0].get("message", {})
    answer = message.get("content", "")
    return answer

def judge_winner(team_a_statements, team_b_statements, topic):
    # 调用API来进行裁判判决并评分
    prompt = (
    f"你是关于'{topic}'这一辩题的辩论裁判。\n\n"
    f"辩论双方陈述内容：\n"
    f"正方(Team A)陈述：{team_a_statements}\n"
    f"反方(Team B)陈述：{team_b_statements}\n\n"
    f"裁判任务：\n"
    f"1. 判定获胜方\n"
    f"2. 为双方分别给出0-100分的评分\n"
    f"3. 详细说明评分理由（每队至少50字）\n\n"
    f"输出要求：\n"
    f"1. 严格使用以下JSON格式，不包含任何其他文本：\n"
    f"""{{
        "winner": "Team A/Team B",
        "scores": {{
            "Team A": 0-100之间的整数,
            "Team B": 0-100之间的整数
        }},
        "reasons": {{
            "Team A": "具体评分理由，需包含论点质量、逻辑连贯性、反驳有效性等方面",
            "Team B": "具体评分理由，需包含论点质量、逻辑连贯性、反驳有效性等方面"
        }}
    }}"""
    f"2. 'winner'字段必须是'Team A'或'Team B'\n"
    f"3. 'scores'中的数值必须为整数，且两队分数不同\n"
    f"4. 'reasons'中的理由需具体且有针对性，避免泛泛而谈\n\n"
    f"示例输出：\n"
    f"""{{
        "winner": "Team B",
        "scores": {{
            "Team A": 75,
            "Team B": 82
        }},
        "reasons": {{
            "Team A": "正方在论点创新性上表现出色，提出了三个独特的解决方案，但在数据支持方面存在不足，且未能有效回应反方关于成本效益的质疑。逻辑链条有断裂，特别是在第三个论点的推导过程中。",
            "Team B": "反方论点构建严谨，每个主张都有具体案例和数据支撑。对正方的核心观点进行了有效反驳，尤其是指出了正方方案中的可行性漏洞。团队协作流畅，角色分工明确。"
        }}
    }}"""
)
    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a fair and impartial judge."},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False},
    )
    json_data = response.model_dump_json()
    data_js = json.loads(json_data)
    message = data_js["choices"][0].get("message", {})
    content = message.get("content", "").strip()
    try:
        judgment_dict = extract_json(content)
        winner = judgment_dict['winner']
        scores = judgment_dict['scores']
        reasons = judgment_dict['reasons']
    except (json.JSONDecodeError, KeyError):
        winner = "无法判断"
        scores = {'Team A': 0, 'Team B': 0}
        reasons = {'Team A': "无法解析JSON", 'Team B': "无法解析JSON"}

    return winner, scores, reasons

def deba(choice):
    options={
        'A':Debater(
    name="特朗普",
    personality="强势张扬，言辞犀利，擅长煽动情绪",
    style="特朗普以商界大亨的身份闻名于世，是美国第45任总统。在辩论中，他会以'美国优先'为核心理念，用'让美国再次伟大'的口号激励听众。他善于使用夸张修辞和短句制造冲击力，如'没有人比我更懂这个'，强调个人成就与果断决策的重要性。其语言充满攻击性却极具感染力，像飓风般席卷全场，凭借强势人格引导舆论走向。"
),
        'B':Debater(
    name="拜登",
    personality="温和稳重，富有同理心，注重传统价值",
    style="拜登是美国第46任总统，以亲民形象和‘重建美好未来’的理念著称。在辩论中，他会引用自己多年的从政经验，强调团结、包容与制度建设的重要性。他的表达方式平实而富有情感，常用‘这里需要的是常识’来呼吁理性与秩序。其语调低沉却坚定，如老树盘根般给人稳定可靠之感，以国家责任与集体利益赢得听众认同。"
),
        'C':Debater(
    name="刘邦",
    personality="机变灵活，知人善任，务实而不拘小节",
    style="刘邦是汉朝开国皇帝，出身布衣却最终战胜项羽，建立四百年汉室江山。在辩论中，他会以‘成大事者不拘小节’为信条，讲述自己如何用人、忍辱负重、因时制宜的故事。他善于用‘得民心者得天下’的道理说明权谋与实用主义的价值。其言辞圆滑而有分寸，如江河入海般顺势而为，以结果导向说服听众接受现实主义立场。"
),
        'D':Debater(
    name="项羽",
    personality="勇猛刚烈，重情重义，宁折不弯",
    style="项羽是秦末西楚霸王，以‘力拔山兮气盖世’的英雄气概闻名于世。在辩论中，他会以‘不肯过江东’的悲壮故事为引，强调气节、荣誉与忠诚的重要性。他推崇‘士为知己者死’的信念，反对苟且偷生与背信弃义。其言辞慷慨激昂，如雷霆万钧，虽败犹荣的形象令人心生敬仰，引导听众认同理想主义的价值观。"
),
        'E':Debater(
    name="朱元璋",
    personality="铁腕果断，多疑善谋，极富执行力",
    style="朱元璋是明朝开国皇帝，从乞丐到帝王的传奇人物。在辩论中，他会以自己早年颠沛流离的经历说明‘生于忧患’的重要性，并强调严刑峻法与集权统治对社会稳定的必要性。他善于用‘乱世当用重典’等观点反驳仁政论者。其语气严厉冷峻，如寒风刺骨，以强权逻辑引导听众认同现实治理中的强硬手段。"
),
        'F':Debater(
    name="皇太极",
    personality="睿智深远，胸怀大局，善于整合资源",
    style="皇太极是清朝奠基者之一，以卓越的政治智慧统一女真各部并改国号为清。在辩论中，他会强调‘兼容并包、满汉一体’的战略眼光，主张通过联合而非征服达成长远目标。他善于用‘文武兼备’的方式阐述治国安邦之道。其言辞沉稳有力，如长城般厚重，以民族融合与战略远见赢得听众对其政策的理解与支持。"
),

        'G':Debater(
    name="鲁迅",
    personality="冷峻犀利，批判精神强烈，思想深邃",
    style="鲁迅是中国现代文学巨匠，以‘横眉冷对千夫指’的姿态直面社会弊病。在辩论中，他会以《狂人日记》《阿Q正传》等作品为例，揭露封建礼教与国民劣根性，强调思想启蒙与文化觉醒的重要性。其语言如匕首投枪，一针见血，常以‘救救孩子’等警句唤醒麻木的心灵，以批判者的身份推动听众反思现状。"
),

        'H':Debater(
    name="郭沫若",
    personality="浪漫激情，才华横溢，兼具学者与革命家气质",
    style="郭沫若是中国现代著名诗人、历史学家与政治活动家。在辩论中，他会以《女神》等诗作展现澎湃的理想主义情怀，同时结合他对甲骨文与古代史的研究，论证文化自信与民族复兴的关系。其言辞如火焰般热烈，又如星辰般闪耀，以学者的深度与诗人的热情引导听众认同进步与变革的方向。"
)
    }
    if choice=='S':
        name_=input("请输入辩手姓名")
        personality_=input("请输入辩手个性")
        style_=input("请输入辩手特点")
        dbter=Debater(name=name_,personality=personality_,style=style_)
    else:
        dbter=options[choice]
    return dbter
def main():
    # 用户输入选题
    topic = input("请输入辩论选题: ")
    debaters=[]

    #选择/自定义比赛队员
    choiceA1 = input("请选择正方一号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceA2 = input("请选择正方二号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceA3 = input("请选择正方三号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceA4 = input("请选择正方四号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()

    choiceB1 = input("请选择反方一号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceB2 = input("请选择反方二号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceB3 = input("请选择反方三号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()
    choiceB4 = input("请选择反方四号辩手（请输入选项前大写字母）：\nA.特朗普 B.拜登 C.刘邦 D.项羽 E.朱元璋 F.皇太极 G.鲁迅 H.郭沫若\nS.自定义").upper()

    choices=[choiceA1,choiceA2,choiceA3,choiceA4,choiceB1,choiceB2,choiceB3,choiceB4]
    defaults=['A','B','C','D','E','F','H','G','S']
    
    for choice in choices:
        if choice in defaults:
            debaters.append(deba(choice))
        else:
            print("代码即将报错，请重新运行")

 

    # 分配辩手到队伍
    team_a = debaters[:4]
    team_b = debaters[4:]

    # 设定队长
    captain_a = TeamCaptain(name="Alice", role="正方", personality="自信", style="逻辑清晰", debaters=team_a)
    captain_b = TeamCaptain(name="Eve", role="反方", personality="严谨", style="细致入微", debaters=team_b)

    # 辩论开始
    round_number = 1
    max_rounds = 2
    team_a_statements = []
    team_b_statements = []

    while round_number <= max_rounds:
        print(f"\n第{round_number}轮辩论:")

        # 正方发言
        speaker_a, reason_a = captain_a.choose_speaker(team_b_statements, team_a_statements, topic)
        print(f"正方队长({captain_a.role})选择出战队员: {speaker_a.name}")
        print(f"选择原因: {reason_a}")
        statement_a = get_debater_response_a(speaker_a, topic, team_b_statements[-1] if team_b_statements else "无")
        print(f"{speaker_a.name} ({captain_a.role}): {statement_a}")
        voice_func(statement_a)
        # 将发言人信息嵌入到陈述内容中
        statement_with_speaker = {
    "speaker": speaker_a.name,
    "role": captain_a.role,
    "content": statement_a
}
        team_a_statements.append(statement_with_speaker)

        # 检查正方是否认输
        concede_a, reason_concede_a = captain_a.decide_to_concede(team_a_statements, topic)
        if concede_a:
            print(f"正方队长({captain_a.role})决定认输！原因: {reason_concede_a}")
            print("反方获胜！")
            break
        else:
            print(f"正方队长({captain_a.role})信心满满！原因: {reason_concede_a}")

        # 反方发言
        speaker_b, reason_b = captain_b.choose_speaker(team_a_statements, team_b_statements, topic)
        print(f"反方队长({captain_b.role})选择出战队员: {speaker_b.name}")
        print(f"选择原因: {reason_b}")
        statement_b = get_debater_response_b(speaker_b, topic, team_a_statements[-1])
        print(f"{speaker_b.name} ({captain_b.role}): {statement_b}")
        voice_func(statement_b)
        statement_with_speaker = {
    "speaker": speaker_b.name,
    "role": captain_b.role,
    "content": statement_b
}
        team_b_statements.append(statement_with_speaker)

        # 检查反方是否认输
        concede_b, reason_concede_b = captain_b.decide_to_concede(team_b_statements, topic)
        if concede_b:
            print(f"反方队长({captain_b.role})决定认输！原因: {reason_concede_b}")
            print("正方获胜！")
            break
        else:
            print(f"反方方队长({captain_a.role})信心满满！原因: {reason_concede_a}")

        round_number += 1

    # 如果达到最大轮数，由AI裁判判决
    if round_number > max_rounds:
        winner, scores, reasons = judge_winner(team_a_statements, team_b_statements, topic)
        print(f"\n辩论结束，裁判判决:")
        print(f"胜者: {winner}")
        print(f"得分: Team A - {scores['Team A']}, Team B - {scores['Team B']}")
        print(f"理由: Team A - {reasons['Team A']}")
        print(f"       Team B - {reasons['Team B']}")

if __name__ == "__main__":
    main()



