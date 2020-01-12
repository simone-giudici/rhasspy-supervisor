"""Tools for generating supervisord conf files for Rhasspy"""
import logging
import shlex
import typing

from rhasspyprofile import Profile

_LOGGER = logging.getLogger(__name__)

# TODO: Add support for "command" systems


def profile_to_conf(
    profile: Profile,
    out_file: typing.TextIO,
    local_mqtt_port=12183,
):
    """Generate supervisord conf from Rhasspy profile"""

    def write_boilerplate():
        """Write boilerplate settings"""
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

    remote_mqtt = profile.get("mqtt.enabled", False)
    if remote_mqtt:
        # Use external broker
        mqtt_username = str(profile.get("mqtt.username", "")).strip()
        mqtt_password = str(profile.get("mqtt.password", "")).strip()

        if mqtt_username:
            # Add username/password
            mqtt_settings["mqtt_username"] = mqtt_username
            mqtt_settings["mqtt_password"] = mqtt_password
    else:
        # Use internal broker (mosquitto) on custom port
        mqtt_settings["mqtt_host"] = "localhost"
        mqtt_settings["mqtt_port"] = local_mqtt_port
        print_mqtt(
            out_file,
            mqtt_port=mqtt_settings["mqtt_port"],
        )
        write_boilerplate()

    # -------------------------------------------------------------------------

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system not in ["dummy", "hermes"]:
        print_microphone(mic_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Microphone disabled (system=%s)", mic_system)

    # Speakers
    sound_system = profile.get("sounds.system", "dummy")
    if sound_system not in ["dummy", "hermes"]:
        print_speakers(sound_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Speakers disabled (system=%s)", sound_system)

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if mic_system not in ["dummy", "hermes"]:
        print_wake(wake_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Wake word disabled (system=%s)", wake_system)

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system != "dummy":
        print_speech_to_text(stt_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Speech to text disabled (system=%s)", stt_system)

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system != "dummy":
        print_intent_recognition(intent_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Intent recognition disabled (system=%s)", intent_system)

    # Text to Speech
    tts_system = profile.get("text_to_speech.system", "dummy")
    if tts_system != "dummy":
        print_text_to_speech(tts_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Text to speech disabled (system=%s)", tts_system)

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system != "dummy":
        print_dialogue(dialogue_system, profile, out_file, **mqtt_settings)
        write_boilerplate()
    else:
        _LOGGER.debug("Dialogue disabled (system=%s)", dialogue_system)


# -----------------------------------------------------------------------------


def print_mqtt(
    out_file: typing.TextIO, mqtt_port: int
):
    """Print command for internal MQTT broker"""
    mqtt_command = ["mosquitto", "-p", str(mqtt_port)]

    print("[program:mqtt]", file=out_file)
    print("command=", " ".join(mqtt_command), sep="", file=out_file)

    # Ensure broker starts first
    print("priority=0", file=out_file)


# -----------------------------------------------------------------------------


def print_webserver(
    profile: Profile, out_file: typing.TextIO, mqtt_host: str, mqtt_port: int, **kwargs
):
    """Print command for Rhasspy web server (http://localhost:12101)"""
    web_command = [
        "rhasspy-server-hermes",
        "--profile",
        profile.name,
        "--system-profiles",
        str(profile.system_profiles_dir),
        "--user-profiles",
        str(profile.user_profiles_dir),
        "--web-dir",
        "web",
        "--mqtt-host",
        str(mqtt_host),
        "--mqtt-port",
        str(mqtt_port),
    ]

    print("[program:web]", file=out_file)
    print("command=", " ".join(web_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add chunk sizes


def print_microphone(
    mic_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for microphone system"""
    assert mic_system in [
        "arecord",
        "pyaudio",
    ], "Only arecord/pyaudio are supported for microphone.system"

    if mic_system == "arecord":
        record_command = [
            "arecord",
            "-q",
            "-r",
            "16000",
            "-f",
            "S16_LE",
            "-c",
            "1",
            "-t",
            "raw",
        ]
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
    elif mic_system == "pyaudio":
        mic_command = [
            "rhasspy-microphone-pyaudio-hermes",
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
        ]

        mic_device = profile.get("microphone.pyaudio.device", "").strip()
        if mic_device:
            mic_command.extend(["--device-index", str(mic_device)])

    print("[program:microphone]", file=out_file)
    print("command=", " ".join(mic_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for precise


def print_wake(
    wake_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for wake system"""
    assert wake_system in [
        "porcupine",
        "snowboy",
    ], "Only porcupine/snowboy are supported for wake.system"

    if wake_system == "porcupine":
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
    elif wake_system == "snowboy":
        wake_command = [
            "rhasspy-wake-snowboy-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
        ]

        # Default settings
        sensitivity = str(profile.get("wake.snowboy.sensitivity", "0.5"))
        audio_gain = float(profile.get("wake.snowboy.audio_gain", "1.0"))
        apply_frontend = bool(profile.get("wake.snowboy.apply_frontend", False))

        model_names: typing.List[str] = profile.get(
            "wake.snowboy.model", "snowboy/snowboy.umdl"
        ).split(",")

        model_settings: typing.Dict[str, typing.Dict[str, typing.Any]] = profile.get(
            "wake.snowboy.model_settings", {}
        )

        for model_name in model_names:
            # Add default settings
            settings = model_settings.get(model_name, {})
            if "sensitivity" not in settings:
                settings["sensitivity"] = sensitivity

            if "audio_gain" not in settings:
                settings["audio_gain"] = audio_gain

            if "apply_frontend" not in settings:
                settings["apply_frontend"] = apply_frontend

            model_path = profile.read_path(model_name)
            model_args = [
                str(model_path),
                str(settings["sensitivity"]),
                str(settings["audio_gain"]),
                str(settings["apply_frontend"]),
            ]
            wake_command.extend(["--model"] + model_args)

    print("[program:wake_word]", file=out_file)
    print("command=", " ".join(wake_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for remote


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
        # Pocketsphinx
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
        # Kaldi
        model_dir = profile.get("speech_to_text.kaldi.model_dir")
        assert model_dir
        model_dir = profile.read_path(model_dir)

        graph = profile.get("speech_to_text.kaldi.graph")
        assert graph
        graph = model_dir / graph

        stt_command = [
            "rhasspy-asr-kaldi-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--model-dir",
            shlex.quote(str(model_dir)),
            "--graph-dir",
            shlex.quote(str(graph)),
        ]

    print("[program:speech_to_text]", file=out_file)
    print("command=", " ".join(stt_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for remote, fuzzywuzzy, adapt, rasaNLU, flair


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

    print("[program:intent_recognition]", file=out_file)
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

    print("[program:dialogue]", file=out_file)
    print("command=", " ".join(dialogue_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for remote, flite, picotts, MaryTTS, Google, NanoTTS


def print_text_to_speech(
    tts_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for text to speech system"""
    assert tts_system in [
        "espeak"
    ], "Only espeak is supported for text_to_speech.system"

    if tts_system == "espeak":
        tts_command = ["espeak", "--stdout"]
        voice = profile.get("text_to_speech.espeak.voice", "").strip()
        if not voice:
            voice = profile.get("language", "").strip()

        if voice:
            tts_command.extend(["-v", str(voice)])

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--tts-command",
            shlex.quote(" ".join(tts_command)),
        ]

    print("[program:text_to_speech]", file=out_file)
    print("command=", " ".join(tts_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def print_speakers(
    sound_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for audio output system"""
    assert sound_system in ["aplay"], "Only aplay is supported for sounds.system"

    play_command = ["aplay", "-q", "-t", "wav"]
    sound_device = profile.get("sounds.arecord.device", "").strip()
    if sound_device:
        play_command.extend(["-D", str(sound_device)])

    play_command = [
        "rhasspy-speakers-cli-hermes",
        "--debug",
        "--siteId",
        str(siteId),
        "--host",
        str(mqtt_host),
        "--port",
        str(mqtt_port),
        "--play-command",
        shlex.quote(" ".join(play_command)),
    ]

    print("[program:speakers]", file=out_file)
    print("command=", " ".join(play_command), sep="", file=out_file)
