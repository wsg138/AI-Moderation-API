#!/usr/bin/env python3
"""G14 synthetic batch generator: third-party self-harm concern.
Seeded for reproducibility. Writes data/synthetic/G14-self-harm-third-party.jsonl
"""
import json
import random

rng = random.Random(14072026)

NAMES_IRL = ["Jake", "Mike", "Alex", "Sam", "Chris", "Tyler", "Ryan", "Ethan",
             "Liam", "Noah", "Lucas", "Mason", "Logan", "Carter", "Dylan", "Leo",
             "Max", "Ben", "Owen", "Luke", "Jack", "Henry", "Milo", "Finn",
             "Nina", "Mia", "Emma", "Sophia", "Ava", "Olivia", "Chloe", "Lily"]
NAMES_MC = ["xX_Shadow_Xx", "crafty_joe", "EnderKing", "PixelPanda", "BlockyBen",
            "DiamondDude", "CreeperHugz", "MineLord99", "NetherNate", "SlimeSam",
            "GolemGary", "RedstoneRita", "VillageVic", "LuckyLuke", "DarkSteve",
            "ObsidianOllie", "TorchTom", "BedrockBob", "ShulkerSue", "PhantomPhil",
            "AxolotlAmy", "WardenWill", "SculkSara", "TrialTheo"]

def nm_irl():
    return rng.choice(NAMES_IRL)

def nm_mc():
    return rng.choice(NAMES_MC)

def nm_any():
    return rng.choice(NAMES_IRL + NAMES_MC)

records = []
_eid = 0

_used_texts = set()

def _uc(cores, name_fn=None):
    """Pick a core, format it, guarantee batch-unique text (retries with new draws)."""
    for _ in range(2000):
        c = rng.choice(cores)
        t = c.format(name=name_fn()) if (name_fn and "{name}" in c) else c
        if t not in _used_texts:
            _used_texts.add(t)
            return t
    raise RuntimeError("exhausted unique cores")

def _uc2(frames):
    """Two-slot variant for quote frames: {name} and {q} re-rolled per retry."""
    for _ in range(2000):
        c = rng.choice(frames)
        t = c.format(name=nm_mc(), q=rng.choice([
            "i can't do this anymore",
            "everyone would be better off without me",
            "i'm done trying",
            "what's the point of any of this",
            "i just want it all to stop",
            "nobody would even care if i was gone",
            "i'm tired of being alive",
            "goodbye everyone, it was fun",
        ]))
        if t not in _used_texts:
            _used_texts.add(t)
            return t
    raise RuntimeError("exhausted unique quote frames")

def _uniq_msg_texts(msgs):
    return " || ".join(m["text"] for m in msgs)


LABEL_DEFAULTS = {
    "THIRD_PARTY_SELF_HARM_CONCERN": dict(action="REVIEW", review_priority="URGENT",
        strike=False, containment="NONE", containment_duration_seconds=None,
        support_flow="SELF_HARM_CHECK"),
    "SAFE": dict(action="ALLOW", review_priority="NONE",
        strike=False, containment="NONE", containment_duration_seconds=None,
        support_flow="NONE"),
    "AMBIGUOUS_REVIEW": dict(action="REVIEW", review_priority="NORMAL",
        strike=False, containment="NONE", containment_duration_seconds=None,
        support_flow="NONE"),
}

PLATFORM_OF = {
    "minecraft_public": "minecraft", "minecraft_private": "minecraft",
    "discord_gaming": "discord", "discord_general": "discord",
}

def add(family_id, label, difficulty, channel_profile, messages, target_index,
        reason_codes, notes, domain="self_harm"):
    global _eid
    _eid += 1
    d = LABEL_DEFAULTS[label]
    rec = {
        "example_id": f"G14-{_eid:04d}",
        "policy_version": "v1",
        "source": "synthetic",
        "domain": domain,
        "difficulty": difficulty,
        "platform_hint": PLATFORM_OF[channel_profile],
        "channel_profile": channel_profile,
        "messages": messages,
        "target_index": target_index,
        "label": label,
        "action": d["action"],
        "review_priority": d["review_priority"],
        "strike": d["strike"],
        "containment": d["containment"],
        "containment_duration_seconds": d["containment_duration_seconds"],
        "support_flow": d["support_flow"],
        "reason_codes": reason_codes,
        "notes": notes,
        "family_id": family_id,
    }
    records.append(rec)

def M(speaker, text, offset_ms=0):
    return {"speaker": speaker, "offset_ms": offset_ms, "text": text}

def chan():
    return rng.choice(["minecraft_public", "minecraft_public", "minecraft_public",
                       "minecraft_private", "discord_gaming", "discord_gaming",
                       "discord_general"])

CONCERN = "THIRD_PARTY_SELF_HARM_CONCERN"
TPC = "third_party_self_harm_concern"

# ---------------------------------------------------------------- easy: direct reports
def fam_friend_direct(n):
    fam = "g14.friend-direct.001"
    cores = [
        "my friend just told me he wants to kill himself, what do i do",
        "my friend just said he's going to kill himself, i'm freaking out",
        "my best friend told me he doesn't want to live anymore",
        "my friend keeps saying he wants to die, i don't know what to do",
        "my irl friend just texted me saying he's done with life",
        "my friend told me tonight that he wants to end it all",
        "my friend said he can't do this anymore and i'm really scared for him",
        "my close friend just admitted he wants to hurt himself",
        "my friend told me he's been thinking about killing himself",
        "my buddy just called me crying saying he wants to die",
        "my friend said life isn't worth it anymore and hung up",
        "my friend told me he's giving up and i don't know how to help",
        "my friend just broke down telling me he wants to die",
        "my best mate said he's done living, i'm panicking",
        "my friend told me he's been planning to kill himself",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Direct report of a friend expressing suicidal intent; urgent staff alert, support resources, no punishment.", )

def fam_friend_cutting(n):
    fam = "g14.friend-cutting.002"
    cores = [
        "my friend told me she's been cutting herself, what should i do",
        "my friend showed me cuts on her arm and i'm really worried",
        "my friend admitted she's been hurting herself lately",
        "my friend told me she cuts when she's stressed, i'm scared for her",
        "she told me she's been self harming and made me promise not to tell",
        "my friend has fresh cuts and i don't know who to tell",
        "my friend said she's been cutting again after stopping for months",
        "i saw cuts on my friend's wrist yesterday, what do i do",
        "my friend told me she hurts herself when no one's around",
        "she showed me scars and said she did it again last night",
        "my friend said the cutting is the only thing that helps",
        "i'm worried, my friend keeps hurting herself",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Report of a friend self-injuring; urgent staff alert, support resources, no punishment.")

def fam_sibling(n):
    fam = "g14.sibling.003"
    cores = [
        "my brother said he wants to die, i'm really scared",
        "my little brother told me he doesn't want to be alive anymore",
        "my sister said she wants to kill herself last night",
        "my older brother keeps saying life is pointless and i'm worried",
        "my sister told me she's been thinking about ending it",
        "my brother locked himself in his room saying he wants to die",
        "my little sister said she wants to disappear forever",
        "my brother told mom he's fine but told me he wants to die",
        "my sister's been crying saying she can't go on",
        "my brother said everyone's better off without him",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Sibling expressing suicidal intent; urgent staff alert, support resources, no punishment.")

def fam_schoolmate(n):
    fam = "g14.schoolmate.004"
    cores = [
        "a kid at school told me he's going to kill himself tonight, please help",
        "someone in my class said they're going to end it tonight",
        "a guy at school told me he has a plan to kill himself",
        "my classmate said she doesn't want to live anymore",
        "a kid on my bus said he's going to hurt himself when he gets home",
        "someone at school showed me a note about not wanting to be here",
        "a girl in my class said she's going to do it tonight",
        "my lab partner told me he wants to end his life",
        "someone in my grade posted something really dark",
        "a teammate said he doesn't want to be alive anymore",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC, "explicit_real_world_cue"], "third_party_concern: Schoolmate with stated plan/timeframe; urgent staff alert, support resources, no punishment.")

def fam_partner(n):
    fam = "g14.partner.005"
    cores = [
        "my gf just texted me saying she wants to end it all",
        "my boyfriend just told me he's going to kill himself",
        "my gf said she can't do this anymore and stopped replying",
        "my partner just sent me a really scary message about not wanting to live",
        "my bf told me he's done and i can't reach him now",
        "my girlfriend said goodbye in a way that really scared me",
        "my bf just said he's going to do something stupid tonight",
        "my girlfriend told me she's had enough of living",
        "my partner said 'i can't do this anymore' and went silent",
        "my gf keeps saying she wants to disappear",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Partner expressing suicidal intent; urgent staff alert, support resources, no punishment.")

def fam_guildmate(n):
    fam = "g14.guildmate.006"
    cores = [
        "one of our guild members said he doesn't want to be here anymore",
        "a guildmate just said in vc he wants to die, can someone check on him",
        "{name} said he can't keep going, i'm worried about him",
        "our teammate has been saying dark stuff about not wanting to live",
        "{name} told the guild he's thinking about ending it",
        "a clan member said goodbye like he meant it forever",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "easy", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Online community member expressing suicidal intent; urgent staff alert, support resources, no punishment.")

def fam_cousin_family(n):
    fam = "g14.cousin-family.007"
    cores = [
        "my cousin told me she wants to hurt herself",
        "my cousin said she doesn't see a reason to keep going",
        "a family member told me he's thinking about suicide",
        "my cousin has been talking about not wanting to wake up",
        "my relative said life feels pointless and i'm worried",
        "my little cousin said she wishes she was never born",
        "my uncle told me he's thinking about ending it",
        "my cousin's been saying dark things about dying",
    ]
    for _ in range(n):
        add(fam, CONCERN, "easy", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Family member expressing self-harm intent; urgent staff alert, support resources, no punishment.")

# ---------------------------------------------------------------- medium: quoting
def fam_quote_chat(n):
    fam = "g14.quote-chat.008"
    quotes = [
        "i can't do this anymore",
        "everyone would be better off without me",
        "i'm done trying",
        "what's the point of any of this",
        "i just want it all to stop",
        "nobody would even care if i was gone",
        "i'm tired of being alive",
        "goodbye everyone, it was fun",
    ]
    frames = [
        "did anyone else see what {name} just said? \"{q}\"",
        "{name} just typed \"{q}\" in chat, that's worrying",
        "hey did you guys see {name}'s message: \"{q}\"",
        "\"{q}\" - that was {name} just now, is he okay",
        "{name} just said \"{q}\" and went offline",
        "someone check on {name}, he just wrote \"{q}\"",
    ]
    for _ in range(n):
        t = _uc2(frames)
        add(fam, CONCERN, "medium", chan(), [M("A", t)], 0,
            [TPC, "quoted_or_condemned"], "third_party_concern: Reporter quoting another player's concerning message verbatim; quoted content is evidence, not endorsement; urgent staff alert.")

def fam_quote_goodbye(n):
    fam = "g14.quote-goodbye.009"
    cores = [
        "{name} just said 'goodbye everyone' and logged off, that felt really final",
        "{name} typed 'it was nice knowing you guys' and left the server",
        "he said 'thanks for everything' in chat and disconnected, i'm worried",
        "{name}'s last message was 'goodbye forever' before he went offline",
        "she just wrote 'i'm sorry everyone' and logged out, that scared me",
        "{name} said 'take care of my base, i won't be back' and left",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "medium", chan(), [M("A", t)], 0,
            [TPC, "quoted_or_condemned"], "third_party_concern: Goodbye-style message from another player reported as concerning; urgent staff alert, support resources.")

def fam_quote_dm(n):
    fam = "g14.quote-dm.010"
    cores = [
        "he dmed me saying he wants to die, i don't know what to do",
        "she sent me a dm: 'i can't keep going like this', i'm scared for her",
        "my friend dmed me 'i'm going to end it tonight', please help",
        "got a dm from {name}: 'nobody cares anyway, goodbye', what do i do",
        "he messaged me privately that he's thinking about killing himself",
        "{name} dmed me a really dark message about not wanting to live",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "medium", chan(), [M("A", t)], 0,
            [TPC, "private_context_relevant"], "third_party_concern: Concerning DM from another player shared by recipient; urgent staff alert, support resources.")

def fam_voice_chat(n):
    fam = "g14.voice-chat.015"
    cores = [
        "he said on vc last night that he wanted to die, i'm worried",
        "{name} was crying on voice chat saying he can't do this anymore",
        "on vc yesterday he kept saying life isn't worth living",
        "she broke down on voice chat talking about ending it",
        "he said over voice that he's thinking about hurting himself",
    ]
    for _ in range(n):
        t = _uc(cores, nm_any)
        add(fam, CONCERN, "medium", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Report of concerning statements made on voice chat; urgent staff alert, support resources.")

def fam_stream_chat(n):
    fam = "g14.stream-chat.016"
    cores = [
        "someone in the stream chat just said they're going to kill themselves",
        "a viewer keeps spamming that they want to die, can a mod do something",
        "{name} in chat said 'goodbye stream, i'm done', that worried me",
        "someone in {name}'s chat is talking about ending their life",
        "a chatter said they don't want to be alive anymore",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "medium", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Concerning message from a stream viewer reported; urgent staff alert, support resources.")

# ---------------------------------------------------------------- medium: help-seeking
def fam_how_to_help(n):
    fam = "g14.how-to-help.011"
    cores = [
        "how do i help my friend who wants to hurt themselves",
        "my friend is talking about suicide, how am i supposed to help him",
        "what can i do for someone who says they want to die",
        "my best friend needs help and i don't know what to say to him",
        "how do you help someone who keeps talking about ending it",
        "my friend is in a really dark place, how do i support her",
        "what's the right thing to say when someone tells you they want to die",
        "i'm trying to help my friend but i feel useless, what do i do",
        "my friend needs help right now, what do i actually do",
        "someone i care about is suicidal, how do i handle this",
        "i'm with my friend and he's talking about dying, help",
        "what are the right steps when someone tells you they want to die",
        "my friend just confided in me, i don't want to mess this up",
        "how do i convince my friend to get help",
        "my friend won't talk to adults, how can i help him myself",
        "she's pushing everyone away and talking about dying, what do i do",
        "i'm scared i'm going to say the wrong thing to him",
        "what do i do if my friend won't let me call anyone",
    ]
    for _ in range(n):
        add(fam, CONCERN, "medium", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Reporter seeking guidance on helping an at-risk person; provide support resources, urgent staff awareness.")

def fam_resources(n):
    fam = "g14.resources.012"
    cores = [
        "does anyone know a hotline number i can give my friend",
        "where can i find help for my friend who's suicidal",
        "is there a crisis number i can send to someone",
        "my friend needs professional help, where do i point him",
        "are there any resources for teens thinking about suicide",
        "i need a support link to send my friend right now",
        "need a crisis hotline number asap for my friend",
        "where do i find suicide prevention resources",
        "is there a text line for teens in crisis",
        "my friend needs help tonight, what number do i give him",
        "looking for a support hotline i can share",
        "are there online chat options for crisis help",
    ]
    for _ in range(n):
        add(fam, CONCERN, "medium", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Request for crisis resources on behalf of another person; provide support resources, staff awareness.")

def fam_what_to_say(n):
    fam = "g14.what-to-say.013"
    cores = [
        "my friend is talking about suicide, what am i supposed to say to him",
        "he told me he wants to die and i froze, what should i have said",
        "what do you say to someone who says they don't want to live",
        "i don't want to say the wrong thing to my friend right now",
        "she's venting about wanting to hurt herself, how do i respond",
        "what's something actually helpful to say here",
        "he just told me, what words actually help",
        "i'm on the phone with him now, what do i say",
        "she's crying about wanting to die, help me know what to say",
        "what should i avoid saying to someone suicidal",
        "i want to be there for him, what does that sound like",
        "he's venting really dark stuff, how do i respond well",
        "what's the best thing to text someone in crisis",
        "i'm worried anything i say will make it worse",
    ]
    for _ in range(n):
        add(fam, CONCERN, "medium", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Reporter asking how to respond to an at-risk person; provide supportive guidance and resources.")

def fam_should_i_tell(n):
    fam = "g14.should-i-tell.014"
    cores = [
        "my friend told me not to tell anyone but i'm really worried about him",
        "he made me promise not to say anything, but he wants to hurt himself",
        "she said she'd hate me if i told, but i'm scared she'll do something",
        "my friend swore me to secrecy about this, what should i do",
        "he said telling anyone would make it worse, but i'm worried sick",
        "i promised i wouldn't tell, but my friend is talking about dying",
        "she begged me not to tell, but this is serious",
        "do i break my promise if it saves his life",
        "he said he'd never forgive me if i told someone",
        "i'm torn between loyalty and keeping her safe",
        "my friend trusts me but i think i need to tell an adult",
        "is it okay to tell his parents even though he said no",
    ]
    for _ in range(n):
        add(fam, CONCERN, "medium", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Reporter conflicted about breaking confidence; encourage telling a trusted adult/staff, provide resources.")

# ---------------------------------------------------------------- hard: escalation / triggers
def fam_witness_live(n):
    fam = "g14.witness-live.017"
    seen_local = set()
    made = 0
    for _try in range(20000):
        if made >= n:
            break
        name = nm_mc()
        variant = rng.randrange(4)
        if variant == 0:
            msgs = [M("A", f"guys {name} is saying scary stuff in chat right now", -4500),
                    M("B", "like what", -2800),
                    M("A", "he keeps saying he wants to die, someone please check on him", 0)]
        elif variant == 1:
            msgs = [M("A", f"{name} is spiraling in general chat rn", -3900),
                    M("A", "he just said nobody would miss him if he was gone", 0)]
        elif variant == 2:
            msgs = [M("B", f"has anyone talked to {name} today", -5200),
                    M("A", f"yeah he's in vc right now saying he can't do this anymore", -2100),
                    M("A", "i think someone should check on him seriously", 0)]
        else:
            msgs = [M("A", f"uhh {name} just said 'i give up on everything' in chat", -1800),
                    M("A", "he's still typing, this doesn't feel like a joke", 0)]
        sig = _uniq_msg_texts(msgs)
        if sig in _used_texts or sig in seen_local:
            continue
        _used_texts.add(sig)
        seen_local.add(sig)
        add(fam, CONCERN, "hard", chan(), msgs, len(msgs) - 1,
            [TPC, "reply_context"] if len(msgs) > 2 else [TPC],
            "third_party_concern: Live witnessing of concerning statements; urgent staff alert, support resources.")
        made += 1
    assert made == n, f"witness_live made {made}/{n}"

def fam_staff_ping(n):
    fam = "g14.staff-ping.018"
    cores = [
        "can a mod please check on {name}, he's saying worrying stuff",
        "staff please, {name} is talking about hurting himself in chat",
        "hey mods, {name} just said something really concerning, can you check",
        "can someone with perms talk to {name}? he's not doing okay",
        "mod help: {name} keeps saying he wants to die",
        "pinging staff because {name} said something scary and logged off",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "hard", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Direct request for staff to check on an at-risk player; urgent staff alert, support resources.")

def fam_aftermath(n):
    fam = "g14.aftermath.019"
    cores = [
        "my friend tried to hurt himself last night, he's in the hospital now",
        "my friend is in the hospital after trying to end it last night",
        "just found out my buddy tried to kill himself, he's alive but in hospital",
        "my friend attempted last night and i'm shaking, he's okay for now",
        "my buddy is in the ER after last night",
        "he tried to overdose, he's stable now",
        "my friend's in the hospital, i'm freaking out",
        "she tried last night and i just found out",
        "my friend survived an attempt last night",
        "he's okay physically but i'm still shaking",
        "just visited my friend in the hospital",
        "my best friend tried to end it, he's alive",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Report of a recent attempt; the person needs support, reporter needs support resources; urgent staff awareness.")

def fam_relapse(n):
    fam = "g14.relapse.020"
    cores = [
        "he was doing better for months and now he's talking like that again",
        "my friend stopped cutting for a year and just told me she relapsed",
        "she was clean for so long and now she's saying she wants to die again",
        "he seemed okay for months but tonight he's talking about ending it",
        "my friend was in therapy and doing well, now he's spiraling again",
        "she started cutting again after a year clean",
        "he's back to talking about dying after months of being okay",
        "my friend relapsed and i'm terrified",
        "all the progress gone, she's talking like before",
        "he stopped going to therapy and now this",
        "she was happy last month, now she's saying dark things again",
        "my friend's old thoughts are back",
        "he told me the urges came back last night",
        "she said she's struggling again after so long",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Report of relapse after improvement; urgent staff alert, support resources.")

def fam_trigger_breakup(n):
    fam = "g14.trigger-breakup.021"
    cores = [
        "his gf broke up with him and now he's saying he wants to die",
        "my friend got dumped and he's talking about ending it all",
        "she broke up with him yesterday and now he's saying life is pointless",
        "after the breakup he's been saying he doesn't want to be here",
        "they broke up and now he says he has nothing to live for",
        "she left him and he's talking about ending everything",
        "post-breakup he's been saying he wants to die",
        "his relationship ended and now he's spiraling hard",
        "she dumped him over text and he's not okay",
        "after she left, he said life feels empty",
        "the breakup broke him, he's saying scary things",
        "he keeps saying he'll do something drastic since she left",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Breakup-triggered suicidal statements about a friend; urgent staff alert, support resources.")

def fam_trigger_bullying(n):
    fam = "g14.trigger-bullying.022"
    cores = [
        "people keep bullying him at school and he said he can't take it anymore",
        "he's getting harassed everywhere and now he's talking about dying",
        "my friend is being bullied nonstop and said he wants to disappear",
        "the bullying got so bad he's saying he doesn't want to live",
        "everyone's been dogpiling him and now he's talking about ending it",
        "the harassment won't stop and he's talking about dying",
        "kids at school torment him daily, now he wants to disappear",
        "he's bullied online constantly and says he can't take more",
        "everyone mocks him and now he's talking about ending it",
        "the bullying followed him here and he's breaking",
        "she's harassed every day and says she gives up",
        "he told me the bullying makes him want to die",
        "they won't leave him alone and he's losing hope",
        "my friend is a target everywhere he goes",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Bullying-triggered suicidal statements; urgent staff alert for both the bullying and the safety concern.")

def fam_trigger_grades(n):
    fam = "g14.trigger-grades.023"
    cores = [
        "he failed his exams and said there's no point in living anymore",
        "my friend bombed his finals and is talking about killing himself",
        "she didn't get into the program and now she's saying she wants to die",
        "he's convinced he ruined his future and keeps saying dark stuff",
        "she failed and now says she's worthless and wants to die",
        "he's convinced his life is over after failing",
        "my friend didn't pass and is talking about ending it",
        "he says he's a failure and doesn't deserve to live",
        "after the rejection letter she's been saying dark things",
        "he bombed the test he needed and spiraled",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC], "third_party_concern: Academic-failure-triggered suicidal statements; urgent staff alert, support resources.")

def fam_night_message(n):
    fam = "g14.night-message.024"
    cores = [
        "it's 3am and he just sent me a really dark message about not wanting to live",
        "he texted me at 2am saying he's done with everything",
        "just got a late night message from her saying she can't do this anymore",
        "he's been up all night sending me worrying messages",
        "3am and my friend is talking about ending it, i don't know what to do",
        "2am texts from him about not wanting to exist",
        "she's been messaging me all night about giving up",
        "he won't sleep, just keeps sending dark messages",
        "up late and my friend is talking about dying",
        "midnight and she's telling me she can't go on",
        "he's been texting scary stuff for hours now",
        "it's late and he's getting darker by the message",
        "she messaged me at 1am saying she's done",
        "can't sleep, my friend's messages are worrying me",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC, "explicit_real_world_cue"], "third_party_concern: Late-night concerning messages; time context raises urgency; urgent staff alert, support resources.")

def fam_secondhand(n):
    fam = "g14.secondhand.025"
    cores = [
        "my friend told me that his friend is talking about killing himself",
        "i heard from someone that {name} has been saying he wants to die",
        "a mutual friend said {name} isn't doing well mentally at all",
        "word is going around that {name} said something scary last night",
    ]
    for _ in range(n):
        t = _uc(cores, nm_any)
        add(fam, CONCERN, "hard", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Secondhand report; lower certainty but still a safety signal; staff check warranted, no punishment.")

def fam_anonymous_tip(n):
    fam = "g14.anonymous-tip.026"
    cores = [
        "i don't want to say who, but someone on this server needs help right now",
        "not naming names but someone here is talking about hurting themselves",
        "i'd rather not say who, but please check on people tonight",
        "someone i know here is in a bad place, can staff keep an eye out",
        "someone here told me they're planning something, please watch out",
        "i'm worried about a player but i can't say who",
        "a person on this server is not safe right now",
        "please keep an eye on chat tonight, someone needs help",
        "i know someone here is struggling badly",
        "can't give details but someone's in crisis",
    ]
    for _ in range(n):
        add(fam, CONCERN, "hard", chan(), [M("A", _uc(cores))], 0,
            [TPC, "insufficient_context"], "third_party_concern: Anonymous tip with limited detail; still a safety signal; staff awareness, gentle follow-up, no punishment.")

def fam_joking_unsure(n):
    fam = "g14.joking-unsure.027"
    cores = [
        "he keeps joking about killing himself but i can't tell if he's serious",
        "she makes suicide jokes constantly and i'm starting to actually worry",
        "{name} jokes about dying all the time, what if he means it",
        "he laughs it off but he keeps saying he wants to die 'as a joke'",
        "i thought it was just dark humor but now i'm not so sure",
    ]
    for _ in range(n):
        t = _uc(cores, nm_any)
        add(fam, CONCERN, "hard", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Uncertainty about joking vs serious does not negate the safety signal; treat as concern, staff check, no punishment.")

def fam_check_in_ask(n):
    fam = "g14.check-in-ask.028"
    cores = [
        "can someone check if {name} is okay, he went quiet after saying something dark",
        "{name} hasn't replied since his last message worried me, can someone check",
        "has anyone heard from {name}? his last message scared me",
        "could a mod check on {name}, i'm worried after what he said",
    ]
    for _ in range(n):
        t = _uc(cores, nm_mc)
        add(fam, CONCERN, "hard", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Request for welfare check after concerning message and silence; urgent staff alert.")

# ---------------------------------------------------------------- adversarial: concern edge cases
def fam_concern_vs_banter(n):
    fam = "g14.concern-vs-banter.029"
    seen_local = set()
    made = 0
    for _try in range(20000):
        if made >= n:
            break
        name = nm_mc()
        variant = rng.randrange(3)
        if variant == 0:
            msgs = [M("A", f"lol {name} died again, classic", -3200),
                    M("B", f"bro {name} just said in vc he's actually not doing good", -1500),
                    M("A", "wait really? he sounded like he was joking but now i'm worried", 0)]
        elif variant == 1:
            msgs = [M("A", f"we were all roasting each other and then {name} said 'maybe i should just die fr'", -2600),
                    M("A", "everyone laughed but he went quiet after, i think he meant it", 0)]
        else:
            msgs = [M("B", f"{name} stop being dramatic lol", -2000),
                    M("A", f"it's not dramatic, he told me yesterday he's been thinking about it for real", 0)]
        sig = _uniq_msg_texts(msgs)
        if sig in _used_texts or sig in seen_local:
            continue
        _used_texts.add(sig)
        seen_local.add(sig)
        add(fam, CONCERN, "adversarial", chan(), msgs, len(msgs) - 1,
            [TPC, "reply_context", "mutual_banter_evidence"],
            "third_party_concern: Concern embedded in banter context; the banter does not cancel the safety signal; urgent staff alert.")
        made += 1
    assert made == n, f"concern_vs_banter made {made}/{n}"

def fam_delayed_report(n):
    fam = "g14.delayed-report.030"
    cores = [
        "this was yesterday but i'm still worried: my friend said he wanted to die",
        "he said it last night and i didn't know what to do, still worried now",
        "this happened a couple days ago but it's been on my mind: she talked about ending it",
        "i didn't say anything at the time but {name} said something scary yesterday",
    ]
    for _ in range(n):
        t = _uc(cores, nm_any)
        add(fam, CONCERN, "adversarial", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Delayed report; passage of time does not remove the safety signal; staff check still warranted.")

def fam_minimizing_reporter(n):
    fam = "g14.minimizing-reporter.031"
    cores = [
        "it's probably nothing but he said he wants to die and i can't stop thinking about it",
        "i'm sure he's fine but he did say he doesn't want to be alive",
        "maybe i'm overreacting but she said she's thinking about ending it",
        "probably just venting but {name} said he wants to disappear forever",
        "i don't want to make a big deal out of nothing, but he said it twice now",
    ]
    for _ in range(n):
        t = _uc(cores, nm_any)
        add(fam, CONCERN, "adversarial", chan(), [M("A", t)], 0,
            [TPC], "third_party_concern: Reporter minimizing does not negate the reported statements; treat as concern; urgent staff alert.")

def fam_evasion_adjacent(n):
    fam = "g14.evasion-adjacent.032"
    cores = [
        "he said he wants to do the thing, you know, the permanent thing",
        "she said she's thinking about doing something drastic to herself",
        "he keeps saying he wants to 'unalive' himself, i'm worried",
        "my friend said he wants to kermit sewer slide, i think he's serious",
        "she said she wants to 'go to sleep forever', that scared me",
        "he said he wants to 'end his subscription to life'",
        "she keeps saying she wants to 'log out permanently'",
        "my friend said he's 'done with the respawn', i'm scared",
        "he said he wants to 'delete himself', what do i do",
        "she's talking about 'permanent sleep', help",
        "he said 'no more respawns for me' and i'm worried",
        "my friend keeps saying he wants to 'quit the game of life'",
    ]
    for _ in range(n):
        add(fam, CONCERN, "adversarial", chan(), [M("A", _uc(cores))], 0,
            [TPC, "obfuscated_evasion"], "third_party_concern: Euphemistic/algospeak phrasing of third-party suicidal statements; the concern signal survives the euphemism; urgent staff alert.")

# ---------------------------------------------------------------- SAFE hard negatives
def fam_hyperbole_boss(n):
    fam = "g14.hyperbole-boss.033"
    cores = [
        "this boss is killing me, i've died like ten times",
        "the warden is actually killing me rn",
        "this boss fight is going to be the death of me lol",
        "bro this boss keeps killing me",
        "this boss is murdering me lol",
        "i'm getting destroyed by this boss",
        "this boss keeps wiping the floor with me",
        "okay this boss is actually impossible, rip me",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", "minecraft_public", [M("A", _uc(cores))], 0,
            ["gameplay_death_context", "minecraft_gameplay_explicit"],
            "safe: 'killing me' is gameplay hyperbole about boss difficulty; no person at risk.", domain="self_harm")

def fam_hyperbole_grind(n):
    fam = "g14.hyperbole-grind.034"
    cores = [
        "this grind will be the death of me",
        "farming netherite is gonna kill me i swear",
        "this grind is killing me slowly lol",
        "another hour of this and i'm dead",
        "this farm is going to kill me",
        "i'm dying of boredom mining this",
        "this grind is actual torture lol",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", "minecraft_public", [M("A", _uc(cores))], 0,
            ["gameplay_death_context", "minecraft_gameplay_explicit"],
            "safe: Grind hyperbole; 'death' refers to tedious gameplay, no person at risk.", domain="self_harm")

def fam_gameplay_death(n):
    fam = "g14.gameplay-death.035"
    cores = [
        "i keep dying to the warden, end my suffering",
        "just kill me already, this parkour is impossible",
        "i've died 20 times to this jump, put me out of my misery",
        "kill me now, i lost all my stuff in lava again",
        "someone end me, the ender dragon keeps one-shotting me",
        "i've fallen in lava 5 times, i'm done",
        "this dungeon keeps killing me",
        "rip me, fell off the build again",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", "minecraft_public", [M("A", _uc(cores))], 0,
            ["gameplay_death_context", "minecraft_gameplay_explicit"],
            "safe: 'kill me' is in-game death frustration; explicit gameplay context, no person at risk.", domain="self_harm")

def fam_slang_dead(n):
    fam = "g14.slang-dead.036"
    cores = [
        "i'm dead lol that was so funny",
        "im deceased, that clip killed me",
        "dead chat lol",
        "i'm actually dead after that fail",
        "that joke has me dead",
        "lmaooo i'm dead",
        "that actually killed me, so funny",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", rng.choice(["minecraft_public", "discord_gaming"]), [M("A", _uc(cores))], 0,
            ["mutual_banter_evidence"],
            "safe: 'dead' is laughter slang; positive/banter context, no person at risk.", domain="self_harm")

def fam_item_death(n):
    fam = "g14.item-death.037"
    cores = [
        "rip my hardcore world, it finally died",
        "my pickaxe died after all that mining",
        "rip my netherite gear, it's gone",
        "my hardcore run just died to a baby zombie",
        "my elytra just died to the void",
        "rip my diamond armor",
        "my horse died to a skeleton, f",
        "there goes my beacon, rip",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", "minecraft_public", [M("A", _uc(cores))], 0,
            ["gameplay_death_context", "minecraft_gameplay_explicit"],
            "safe: 'died' refers to items/worlds, not people.", domain="self_harm")

def fam_tired_slang(n):
    fam = "g14.tired-slang.038"
    cores = [
        "i'm dead tired, going to bed",
        "that session wiped me out, i'm dead",
        "i'm exhausted lol, dead on my feet",
        "dead after that raid, gn",
        "i'm so dead, that took forever",
        "wiped out lol, going to sleep",
        "dead tired after building all day",
    ]
    for _ in range(n):
        add(fam, "SAFE", "hard", chan(), [M("A", _uc(cores))], 0,
            ["mutual_banter_evidence"],
            "safe: 'dead' as tiredness slang; no person at risk.", domain="self_harm")

def fam_lyrics_sad(n):
    fam = "g14.lyrics-sad.039"
    cores = [
        "this lyric hits so hard: 'i wanna disappear into the night'",
        "been listening to this song on repeat, 'nobody knows i'm fading away' what a line",
        "quote of the day from my playlist: 'i'm already gone, just a ghost'",
        "that new track 'goodbye world' has been on loop all day",
        "lyrics that live in my head rent free: 'bury me with my sorrows'",
        "on repeat: 'i'm fading like a photograph' - chills",
        "this verse 'goodnight world, i'm checking out' is poetry",
        "'bury my heart in the static' what a lyric",
        "can't stop playing 'elegy for the living', that bridge",
        "'i'll be a ghost in your playlist' - stuck in my head",
    ]
    for _ in range(n):
        add(fam, "SAFE", "adversarial", rng.choice(["discord_gaming", "discord_general"]), [M("A", _uc(cores))], 0,
            ["quoted_or_condemned", "discord_general_no_game_context"],
            "safe: Clearly framed as song lyrics being discussed/appreciated; metalinguistic framing, no person at risk.", domain="self_harm")

def fam_lyrics_mimic(n):
    fam = "g14.lyrics-mimic.040"
    lyric_lines = [
        "'i don't wanna be here anymore'",
        "'say goodbye, i'm leaving tonight'",
        "'what's the point of staying alive'",
        "'i'm already gone, just a ghost'",
        "'bury me with my sorrows'",
        "'goodnight world, i'm checking out'",
        "'nobody knows i'm fading away'",
        "'i'll be a ghost in your playlist'",
        "'take me where the light don't go'",
        "'i'm tired of the sunrise'",
    ]
    openers = [
        "anyone else have that one sad song on repeat",
        "new album just dropped and the lyrics are so dark lol",
        "this artist really gets it",
        "been looping this track all week",
        "this song has been on repeat for days",
    ]
    reactions = [
        "that chorus destroys me",
        "is such a banger line",
        "what a lyric",
        "gives me chills every time",
        "the songwriting is unreal",
    ]
    seen_local = set()
    made = 0
    for _try in range(20000):
        if made >= n:
            break
        variant = rng.randrange(3)
        line = rng.choice(lyric_lines)
        if variant == 0:
            msgs = [M("A", rng.choice(openers), -2400),
                    M("A", f"{line} - {rng.choice(reactions)}", 0)]
        elif variant == 1:
            msgs = [M("A", f"new album just dropped and the lyrics are so dark lol", -1800),
                    M("A", f"{line} {rng.choice(reactions)}", 0)]
        else:
            msgs = [M("A", f"this artist really gets it: {line}", -2100),
                    M("B", "fr that whole album is a masterpiece", -900),
                    M("A", f"right?? {rng.choice(reactions)}", 0)]
        sig = _uniq_msg_texts(msgs)
        if sig in _used_texts or sig in seen_local:
            continue
        _used_texts.add(sig)
        seen_local.add(sig)
        add(fam, "SAFE", "adversarial", rng.choice(["discord_gaming", "discord_general"]), msgs, len(msgs) - 1,
            ["quoted_or_condemned", "reply_context"],
            "safe: Dark lyrics discussed as music; conversational framing confirms artistic context, no person at risk.", domain="self_harm")
        made += 1
    assert made == n, f"lyrics_mimic made {made}/{n}"

def fam_metaphor_dark(n):
    fam = "g14.metaphor-dark.041"
    cores = [
        "this homework will kill me i swear",
        "my sleep schedule is dead after this week",
        "this lag is killing me, fix the server pls",
        "i'm gonna die of embarrassment after that presentation",
        "my brain is dead after that math test",
        "mondays are killing me softly lol",
        "this traffic is killing me",
        "my allergies are murdering me today",
        "this queue is going to be the death of me",
        "my phone died AND my charger broke, rip me",
    ]
    for _ in range(n):
        add(fam, "SAFE", "adversarial", chan(), [M("A", _uc(cores))], 0,
            ["mutual_banter_evidence"],
            "safe: 'kill/die' as everyday hyperbole about non-lethal frustrations; no person at risk.", domain="self_harm")

# ---------------------------------------------------------------- AMBIGUOUS_REVIEW
def fam_vague_worry(n):
    fam = "g14.vague-worry.042"
    cores = [
        "i'm worried about {name}",
        "kinda concerned about {name} lately",
        "i've been worried about {name}",
        "something feels off with {name}",
        "{name} has me worried",
        "not sure what's up with {name} lately",
        "i'm a bit worried for {name}",
        "something's been off with {name}",
    ]
    for _ in range(n):
        add(fam, "AMBIGUOUS_REVIEW", "hard", chan(), [M("A", _uc(cores, nm_any))], 0,
            ["insufficient_context"],
            "ambiguous: Worry expressed with no specifics about self-harm; review to determine if follow-up is warranted.", domain="self_harm")

def fam_vague_absence(n):
    fam = "g14.vague-absence.043"
    cores = [
        "has anyone seen {name} today",
        "{name} hasn't been online in days",
        "anyone heard from {name} lately",
        "haven't seen {name} around",
        "where's {name} been",
        "has {name} been on at all",
        "{name} went quiet, hope all good",
    ]
    for _ in range(n):
        add(fam, "AMBIGUOUS_REVIEW", "hard", chan(), [M("A", _uc(cores, nm_any))], 0,
            ["insufficient_context"],
            "ambiguous: Absence noted with mild concern but no self-harm signal; review, no urgent action.", domain="self_harm")

def fam_vague_mood(n):
    fam = "g14.vague-mood.044"
    cores = [
        "{name}'s been acting off lately",
        "{name}'s been really quiet",
        "my friend's been in a weird mood",
        "{name} hasn't been himself",
        "something's up with {name}'s mood",
        "{name} seems down lately",
    ]
    for _ in range(n):
        add(fam, "AMBIGUOUS_REVIEW", "hard", chan(), [M("A", _uc(cores, nm_any))], 0,
            ["insufficient_context"],
            "ambiguous: Vague mood observation with no self-harm content; review to assess.", domain="self_harm")

def fam_vague_post(n):
    fam = "g14.vague-post.045"
    cores = [
        "did you see what {name} posted",
        "did anyone see {name}'s status",
        "have you seen {name}'s bio",
        "did {name} post something",
    ]
    for _ in range(n):
        add(fam, "AMBIGUOUS_REVIEW", "hard", chan(), [M("A", _uc(cores, nm_any))], 0,
            ["insufficient_context"],
            "ambiguous: References unseen content with no description; cannot assess risk; review.", domain="self_harm")

# Multi-message conversational context injection (target >=55% multi-message).
# Prepends/appends label-neutral context; shifts target_index accordingly.
_CTX_PRE_CONCERN = [
    "hey, what's going on",
    "you seem worried, what happened",
    "is everything okay",
    "what's up, you sound stressed",
]
_CTX_POST_CONCERN = [
    "i'm really scared",
    "please, someone help",
    "i don't know what to do",
    "this can't wait",
]
_CTX_PRE_SAFE = [
    "lol what's up",
    "yo, how's the grind going",
    "anyone on right now",
]
_CTX_POST_SAFE = [
    "anyway, back to mining",
    "lol anyway",
    "good times",
]
_CTX_PRE_AMBIG = [
    "hey",
    "anyone around",
]
_CTX_POST_AMBIG = [
    "just thinking out loud",
    "nvm i guess",
]

def _inject_context():
    import random as _r
    probs = {"easy": 0.45, "medium": 0.68, "hard": 0.78, "adversarial": 0.70}
    for r in records:
        if len(r["messages"]) > 1:
            continue
        p = probs[r["difficulty"]]
        if _r.Random(hash(r["example_id"]) % (2**32)).random() > p:
            continue
        label = r["label"]
        if label == CONCERN:
            pre, post = _CTX_PRE_CONCERN, _CTX_POST_CONCERN
        elif label == "SAFE":
            pre, post = _CTX_PRE_SAFE, _CTX_POST_SAFE
        else:
            pre, post = _CTX_PRE_AMBIG, _CTX_POST_AMBIG
        msgs = r["messages"]
        # prepend context from another speaker
        if rng.random() < 0.7:
            ctx = rng.choice(pre)
            msgs = [M("B", ctx, -2600)] + msgs
            # shift existing offsets? keep target at 0, context negative is fine
            r["target_index"] += 1
        # append follow-up from reporter
        if rng.random() < 0.5:
            msgs = msgs + [M("A", rng.choice(post), 1900)]
        r["messages"] = msgs
        # fix reason codes for added context
        if len(msgs) > 1 and "reply_context" not in r["reason_codes"]:
            # only add reply_context when a real reply relationship exists (prepended)
            if r["target_index"] > 0:
                r["reason_codes"] = r["reason_codes"] + ["reply_context"]

# ---------------------------------------------------------------- driver
PLAN = [
    # (func, count)
    (fam_friend_direct, 15), (fam_friend_cutting, 12), (fam_sibling, 10),
    (fam_schoolmate, 10), (fam_partner, 10), (fam_guildmate, 10),
    (fam_cousin_family, 8),
    (fam_quote_chat, 20), (fam_quote_goodbye, 14), (fam_quote_dm, 14),
    (fam_how_to_help, 18), (fam_resources, 12), (fam_what_to_say, 14),
    (fam_should_i_tell, 12), (fam_voice_chat, 10), (fam_stream_chat, 11),
    (fam_witness_live, 18), (fam_staff_ping, 16), (fam_aftermath, 12),
    (fam_relapse, 14), (fam_trigger_breakup, 12), (fam_trigger_bullying, 14),
    (fam_trigger_grades, 10), (fam_night_message, 14), (fam_secondhand, 12),
    (fam_anonymous_tip, 10), (fam_joking_unsure, 11), (fam_check_in_ask, 12),
    (fam_concern_vs_banter, 12), (fam_delayed_report, 10),
    (fam_minimizing_reporter, 11), (fam_evasion_adjacent, 12),
    (fam_hyperbole_boss, 8), (fam_hyperbole_grind, 7), (fam_gameplay_death, 8),
    (fam_slang_dead, 7), (fam_item_death, 8), (fam_tired_slang, 7),
    (fam_lyrics_sad, 10), (fam_lyrics_mimic, 10), (fam_metaphor_dark, 10),
    (fam_vague_worry, 8), (fam_vague_absence, 7), (fam_vague_mood, 6),
    (fam_vague_post, 4),
]

def main():
    for func, count in PLAN:
        func(count)
    _inject_context()
    assert len(records) == 500, f"got {len(records)}"
    # id uniqueness
    ids = [r["example_id"] for r in records]
    assert len(set(ids)) == 500, "duplicate example_ids"
    # exact text dedup within batch
    texts = [" || ".join(m["text"] for m in r["messages"]) for r in records]
    assert len(set(texts)) == 500, "exact duplicate texts in batch"
    out = "data/synthetic/G14-self-harm-third-party.jsonl"
    with open(out, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records to {out}")
    # distribution summary
    from collections import Counter
    print("labels:", dict(Counter(r["label"] for r in records)))
    print("difficulty:", dict(Counter(r["difficulty"] for r in records)))
    mm = sum(1 for r in records if len(r["messages"]) > 1)
    print(f"multi-message: {mm} ({mm/5:.1f}%)")

if __name__ == "__main__":
    main()
