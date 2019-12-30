"""Tools for generating supervisord conf files for Rhasspy"""
import shlex
import typing

from rhasspyprofile import Profile


def profile_to_conf(profile: Profile, out_file: typing.TextIO):
    """Generate supervisord conf from Rhasspy profile"""

    def write_boilerplate():
        """Write boilerplate settings"""
        print("killasgroup=true", file=out_file)
        print("stopasgroup=true", file=out_file)
        print("stdout_logfile=/dev/stdout", file=out_file)
        print("stdout_logfile_maxbytes=0", file=out_file)
        print("redirect_stderr=true", file=out_file)
        print("", file=out_file)

    # Header
    print("[supervisord]", file=out_file)
    print("nodaemon=true", file=out_file)
    print("", file=out_file)

    # MQTT
    mqtt_settings = {
        "siteId": str(profile.get("mqtt.site_id", "default")),
        "mqtt_host": str(profile.get("mqtt.host", "localhost")),
        "mqtt_port": int(profile.get("mqtt.port", 1883)),
    }

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system != "dummy":
        print_microphone(mic_system, profile, out_file, **mqtt_settings)
        write_boilerplate()

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if mic_system != "dummy":
        print_wake(wake_system, profile, out_file, **mqtt_settings)
        write_boilerplate()

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system != "dummy":
        print_speech_to_text(stt_system, profile, out_file, **mqtt_settings)
        write_boilerplate()

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system != "dummy":
        print_intent_recognition(intent_system, profile, out_file, **mqtt_settings)
        write_boilerplate()

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system != "dummy":
        print_dialogue(dialogue_system, profile, out_file, **mqtt_settings)
        write_boilerplate()


# -----------------------------------------------------------------------------


def print_microphone(
    mic_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for microphone system"""
    assert mic_system in ["arecord"], "Only arecord is supported for microphone.system"

    record_command = ["arecord", "-r", "16000", "-f", "S16_LE", "-c", "1", "-t", "raw"]
    mic_device = profile.get("microphone.arecord.device", "").strip()
    if mic_device:
        record_command.extend(["-D", str(mic_device)])

    mic_command = [
        "rhasspy-microphone-cli-hermes",
        "--debug",
        "--siteId",
        str(siteId),
        "--host",
        str(mqtt_host),
        "--port",
        str(mqtt_port),
        "--sample-rate",
        "16000",
        "--sample-width",
        "2",
        "--channels",
        "1",
        "--record-command",
        shlex.quote(" ".join(record_command)),
    ]

    print("[program:microphone]")
    print("command=", " ".join(mic_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def print_wake(
    wake_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for wake system"""
    assert wake_system in ["porcupine"], "Only porcupine is supported for wake.system"

    library = profile.get("wake.porcupine.library_path")
    assert library

    model = profile.get("wake.porcupine.model_path")
    assert model

    keyword = profile.get("wake.porcupine.keyword_path")
    assert keyword

    sensitivity = profile.get("wake.porcupine.sensitivity", "0.5")

    wake_command = [
        "rhasspy-wake-porcupine-hermes",
        "--debug",
        "--siteId",
        str(siteId),
        "--host",
        str(mqtt_host),
        "--port",
        str(mqtt_port),
        "--library",
        shlex.quote(str(profile.read_path(library))),
        "--model",
        shlex.quote(str(profile.read_path(model))),
        "--keyword",
        shlex.quote(str(profile.read_path(keyword))),
        "--sensitivity",
        str(sensitivity),
    ]

    print("[program:wake_word]")
    print("command=", " ".join(wake_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def print_speech_to_text(
    stt_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for speech to text system"""
    assert stt_system in [
        "pocketsphinx",
        "kaldi",
    ], "Only pocketsphinx/kaldi are supported for speech_to_text.system"

    if stt_system == "pocketsphinx":
        acoustic_model = profile.get("speech_to_text.pocketsphinx.acoustic_model")
        assert acoustic_model

        dictionary = profile.get("speech_to_text.pocketsphinx.dictionary")
        assert dictionary

        language_model = profile.get("speech_to_text.pocketsphinx.language_model")
        assert language_model

        stt_command = [
            "rhasspy-asr-pocketsphinx-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--acoustic-model",
            shlex.quote(str(profile.read_path(acoustic_model))),
            "--dictionary",
            shlex.quote(str(profile.read_path(dictionary))),
            "--language-model",
            shlex.quote(str(profile.read_path(language_model))),
        ]
    elif stt_system == "kaldi":
        # TODO: Add Kaldi support
        pass

    print("[program:speech_to_text]")
    print("command=", " ".join(stt_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def print_intent_recognition(
    intent_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for intent recognition system"""
    assert intent_system in [
        "fsticuffs"
    ], "Only fsticuffs is supported for intent.system"

    graph = profile.get("intent.fsticuffs.intent_graph")
    assert graph

    # TODO: Add fuzzy argument
    intent_command = [
        "rhasspy-nlu-hermes",
        "--debug",
        "--siteId",
        str(siteId),
        "--host",
        str(mqtt_host),
        "--port",
        str(mqtt_port),
        "--graph",
        shlex.quote(str(profile.read_path(graph))),
    ]

    print("[program:intent_recognition]")
    print("command=", " ".join(intent_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def print_dialogue(
    dialogue_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for dialogue management system"""
    assert dialogue_system in ["hermes"], "Only hermes is supported for dialogue.system"

    dialogue_command = [
        "rhasspy-dialogue-hermes",
        "--debug",
        "--siteId",
        str(siteId),
        "--host",
        str(mqtt_host),
        "--port",
        str(mqtt_port),
    ]

    print("[program:dialogue]")
    print("command=", " ".join(dialogue_command), sep="", file=out_file)
