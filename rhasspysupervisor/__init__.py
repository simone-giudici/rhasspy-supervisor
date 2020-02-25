"""Tools for generating supervisord/docker files for Rhasspy"""
import logging
import shlex
import typing

import yaml
from rhasspyprofile import Profile

_LOGGER = logging.getLogger(__name__)

# TODO: Add support for "command" systems

# -----------------------------------------------------------------------------
# supervisord
# -----------------------------------------------------------------------------


def profile_to_conf(profile: Profile, out_file: typing.TextIO, local_mqtt_port=12183):
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
    siteId = str(profile.get("mqtt.site_id", "default"))
    mqtt_host = str(profile.get("mqtt.host", "localhost"))
    mqtt_port = int(profile.get("mqtt.port", 1883))

    # mqtt_username = str(profile.get("mqtt.username", "")).strip()
    # mqtt_password = str(profile.get("mqtt.password", "")).strip()

    remote_mqtt = profile.get("mqtt.enabled", False)
    if not remote_mqtt:
        # Use internal broker (mosquitto) on custom port
        mqtt_host = "localhost"
        mqtt_port = local_mqtt_port
        print_mqtt(out_file, mqtt_port=local_mqtt_port)
        write_boilerplate()

    # -------------------------------------------------------------------------

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system not in {"dummy", "hermes"}:
        print_microphone(
            mic_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Microphone disabled (system=%s)", mic_system)

    # Speakers
    sound_system = profile.get("sounds.system", "dummy")
    if sound_system not in {"dummy", "hermes"}:
        print_speakers(
            sound_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Speakers disabled (system=%s)", sound_system)

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if wake_system not in {"dummy", "hermes"}:
        print_wake(
            wake_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Wake word disabled (system=%s)", wake_system)

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system not in {"dummy", "hermes"}:
        print_speech_to_text(
            stt_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Speech to text disabled (system=%s)", stt_system)

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system not in {"dummy", "hermes"}:
        print_intent_recognition(
            intent_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Intent recognition disabled (system=%s)", intent_system)

    # Intent Handling
    handle_system = profile.get("handle.system", "dummy")
    if handle_system not in {"dummy", "hermes"}:
        print_intent_handling(
            handle_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Intent handling disabled (system=%s)", handle_system)

    # Text to Speech
    tts_system = profile.get("text_to_speech.system", "dummy")
    if tts_system not in {"dummy", "hermes"}:
        print_text_to_speech(
            tts_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Text to speech disabled (system=%s)", tts_system)

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system not in {"dummy", "hermes"}:
        print_dialogue(
            dialogue_system,
            profile,
            out_file,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
        write_boilerplate()
    else:
        _LOGGER.debug("Dialogue disabled (system=%s)", dialogue_system)


# -----------------------------------------------------------------------------


def print_mqtt(out_file: typing.TextIO, mqtt_port: int):
    """Print command for internal MQTT broker"""
    mqtt_command = ["mosquitto", "-p", str(mqtt_port)]

    print("[program:mqtt]", file=out_file)
    print("command=", " ".join(mqtt_command), sep="", file=out_file)

    # Ensure broker starts first
    print("priority=0", file=out_file)


# -----------------------------------------------------------------------------


def print_webserver(
    profile: Profile, out_file: typing.TextIO, mqtt_host: str, mqtt_port: int
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


def get_microphone(
    mic_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for microphone system"""
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
        list_command = ["arecord", "-L"]
        test_command = "arecord -q -D {} -r 16000 -f S16_LE -c 1 -t raw"

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
            "--list-command",
            shlex.quote(" ".join(list_command)),
            "--test-command",
            shlex.quote(test_command),
        ]

        return mic_command

    if mic_system == "pyaudio":
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

        return mic_command

    if mic_system == "command":
        # Command to record audio
        record_program = profile.get("microphone.command.record_program")
        assert record_program, "microphone.command.record_program is required"
        record_command = [record_program] + profile.get(
            "microphone.command.record_arguments", []
        )

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

        # Command to list available audio input devices
        list_program = profile.get("microphone.command.list_program")
        if list_program:
            list_command = [list_program] + profile.get(
                "microphone.command.list_arguments", []
            )
            mic_command.extend(
                ["--list-command", shlex.quote(" ".join(str(v) for v in list_command))]
            )
        else:
            _LOGGER.warning("No microphone device listing command provided.")

        # Command to test available audio input devices
        test_program = profile.get("microphone.command.test_program")
        if test_program:
            test_command = [test_program] + profile.get(
                "microphone.command.test_arguments", []
            )
            mic_command.extend(
                ["--test-command", shlex.quote(" ".join(str(v) for v in test_command))]
            )
        else:
            _LOGGER.warning("No microphone device testing command provided.")

        return mic_command

    raise ValueError(f"Unsupported audio input system (got {mic_system})")


def print_microphone(
    mic_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for microphone system"""
    mic_command = get_microphone(
        mic_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:microphone]", file=out_file)
    print("command=", " ".join(mic_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for precise


def get_wake(
    wake_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for wake system"""
    if wake_system == "porcupine":
        library = profile.get("wake.porcupine.library_path")
        assert library, "wake.porcupine.library_path required"

        model = profile.get("wake.porcupine.model_path")
        assert model, "wake.porcupine.model_path required"

        keyword = profile.get("wake.porcupine.keyword_path")
        assert keyword, "wake.porcupine.keyword_path required"

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
            shlex.quote(str(profile.write_path(library))),
            "--model",
            shlex.quote(str(profile.write_path(model))),
            "--keyword",
            shlex.quote(str(profile.write_path(keyword))),
            "--sensitivity",
            str(sensitivity),
            "--keyword-dir",
            shlex.quote(str(profile.write_path("porcupine"))),
        ]

        return wake_command

    if wake_system == "snowboy":
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

            model_path = profile.write_path(model_name)
            model_args = [
                str(model_path),
                str(settings["sensitivity"]),
                str(settings["audio_gain"]),
                str(settings["apply_frontend"]),
            ]
            wake_command.extend(["--model"] + model_args)

        return wake_command

    if wake_system == "pocketsphinx":
        # Load decoder settings (use speech-to-text configuration as a fallback)
        acoustic_model = profile.get("wake.pocketsphinx.acoustic_model") or profile.get(
            "speech_to_text.pocketsphinx.acoustic_model"
        )
        assert acoustic_model, "acoustic model required"

        dictionary = profile.get("wake.pocketsphinx.dictionary") or profile.get(
            "speech_to_text.pocketsphinx.dictionary"
        )

        assert dictionary, "dictionary required"

        wake_command = [
            "rhasspy-wake-pocketsphinx-hermes",
            "--debug",
            "--keyphrase",
            str(profile.get("wake.pocketsphinx.keyphrase", "okay raspy")),
            "--keyphrase-threshold",
            str(profile.get("wake.pocketsphinx.threshold", "1e-40")),
            "--acoustic-model",
            shlex.quote(str(profile.write_path(acoustic_model))),
            "--dictionary",
            shlex.quote(str(profile.write_path(dictionary))),
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
        ]

        mllr_matrix = profile.get("wake.pocketsphinx.mllr_matrix")
        if mllr_matrix:
            wake_command.extend(
                ["--mllr-matrix", shlex.quote(str(profile.write_path(mllr_matrix)))]
            )

        return wake_command

    if wake_system == "command":
        user_program = profile.get("wake.command.program")
        assert user_program, "wake.command.program is required"
        user_command = [user_program] + profile.get("wake.command.arguments", [])

        wake_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--wake-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        # Audio format
        sample_rate = profile.get("wake.command.sample_rate")
        if sample_rate:
            wake_command.extend(["--wake-sample-rate", str(sample_rate)])

        sample_width = profile.get("wake.command.sample_width")
        if sample_width:
            wake_command.extend(["--wake-sample-width", str(sample_width)])

        channels = profile.get("wake.command.channels")
        if channels:
            wake_command.extend(["--wake-channels", str(channels)])

        return wake_command

    raise ValueError(f"Unsupported wake system (got {wake_system})")


def print_wake(
    wake_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for wake system"""
    wake_command = get_wake(
        wake_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:wake_word]", file=out_file)
    print("command=", " ".join(wake_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def get_speech_to_text(
    stt_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for speech to text system"""
    if stt_system == "pocketsphinx":
        # Pocketsphinx
        acoustic_model = profile.get("speech_to_text.pocketsphinx.acoustic_model")
        assert acoustic_model

        open_transcription = bool(
            profile.get("speech_to_text.pocketsphinx.open_transcription", False)
        )

        if open_transcription:
            dictionary = profile.get("speech_to_text.pocketsphinx.base_dictionary")
            language_model = profile.get(
                "speech_to_text.pocketsphinx.base_language_model"
            )
        else:
            dictionary = profile.get("speech_to_text.pocketsphinx.dictionary")
            language_model = profile.get("speech_to_text.pocketsphinx.language_model")

        assert dictionary, "Dictionary required"
        assert language_model, "Language model required"

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
            shlex.quote(str(profile.write_path(acoustic_model))),
            "--dictionary",
            shlex.quote(str(profile.write_path(dictionary))),
            "--language-model",
            shlex.quote(str(profile.write_path(language_model))),
        ]

        if open_transcription:
            # Don't overwrite dictionary or language model during training
            stt_command.append("--no-overwrite-train")

        base_dictionary = profile.get("speech_to_text.pocketsphinx.base_dictionary")
        if base_dictionary:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(profile.write_path(base_dictionary))),
                ]
            )

        custom_words = profile.get("speech_to_text.pocketsphinx.custom_words")
        if custom_words:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(profile.write_path(custom_words))),
                ]
            )

        # Case transformation for dictionary word
        dictionary_casing = profile.get("speech_to_text.dictionary_casing")
        if dictionary_casing:
            stt_command.extend(["--dictionary-casing", dictionary_casing])

        # Grapheme-to-phoneme model
        g2p_model = profile.get("speech_to_text.pocketsphinx.g2p_model")
        if g2p_model:
            stt_command.extend(
                ["--g2p-model", shlex.quote(str(profile.write_path(g2p_model)))]
            )

        # Case transformation for grapheme-to-phoneme model
        g2p_casing = profile.get("speech_to_text.g2p_casing")
        if g2p_casing:
            stt_command.extend(["--g2p-casing", g2p_casing])

        # Path to write missing words and guessed pronunciations
        unknown_words = profile.get("speech_to_text.pocketsphinx.unknown_words")
        if unknown_words:
            stt_command.extend(
                ["--unknown-words", shlex.quote(str(profile.write_path(unknown_words)))]
            )

        return stt_command

    if stt_system == "kaldi":
        # Kaldi
        model_dir = profile.get("speech_to_text.kaldi.model_dir")
        assert model_dir
        model_dir = profile.write_path(model_dir)

        open_transcription = bool(
            profile.get("speech_to_text.kaldi.open_transcription", False)
        )

        if open_transcription:
            graph = profile.get("speech_to_text.kaldi.base_graph")
        else:
            graph = profile.get("speech_to_text.kaldi.graph")

        assert graph, "Graph directory is required"
        graph = model_dir / graph

        model_type = profile.get("speech_to_text.kaldi.model_type")
        assert model_type, "Model type is required"

        stt_command = [
            "rhasspy-asr-kaldi-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--model-type",
            str(model_type),
            "--model-dir",
            shlex.quote(str(model_dir)),
            "--graph-dir",
            shlex.quote(str(graph)),
        ]

        if open_transcription:
            # Don't overwrite HCLG.fst during training
            stt_command.append("--no-overwrite-train")

        base_dictionary = profile.get("speech_to_text.kaldi.base_dictionary")
        if base_dictionary:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(profile.write_path(base_dictionary))),
                ]
            )

        custom_words = profile.get("speech_to_text.kaldi.custom_words")
        if custom_words:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(profile.write_path(custom_words))),
                ]
            )

        # Case transformation for dictionary word
        dictionary_casing = profile.get("speech_to_text.dictionary_casing")
        if dictionary_casing:
            stt_command.extend(["--dictionary-casing", dictionary_casing])

        # Grapheme-to-phoneme model
        g2p_model = profile.get("speech_to_text.kaldi.g2p_model")
        if g2p_model:
            stt_command.extend(
                ["--g2p-model", shlex.quote(str(profile.write_path(g2p_model)))]
            )

        # Case transformation for grapheme-to-phoneme model
        g2p_casing = profile.get("speech_to_text.g2p_casing")
        if g2p_casing:
            stt_command.extend(["--g2p-casing", g2p_casing])

        # Path to write missing words and guessed pronunciations
        unknown_words = profile.get("speech_to_text.kaldi.unknown_words")
        if unknown_words:
            stt_command.extend(
                ["--unknown-words", shlex.quote(str(profile.write_path(unknown_words)))]
            )

        return stt_command

    if stt_system == "command":
        user_program = profile.get("speech_to_text.command.program")
        assert user_program, "speech_to_text.command.program is required"
        user_command = [user_program] + profile.get(
            "speech_to_text.command.arguments", []
        )

        stt_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--asr-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        # Training
        stt_train_system = profile.get("training.speech_to_text.system", "auto")
        if stt_train_system == "auto":
            train_url = profile.get("training.speech_to_text.remote.url")
            if train_url:
                stt_command.extend(["--asr-train-url", shlex.quote(train_url)])
            else:
                _LOGGER.warning("No speech to text training URL was provided")

        return stt_command

    if stt_system == "remote":
        url = profile.get("speech_to_text.remote.url")
        assert url, "speech_to_text.remote.url is required"

        stt_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--asr-url",
            shlex.quote(url),
        ]

        # Training
        stt_train_system = profile.get("training.speech_to_text.system", "auto")
        if stt_train_system == "auto":
            train_program = profile.get("training.speech_to_text.command.program")
            if train_program:
                train_command = [train_program] + profile.get(
                    "training.speech_to_text.command.arguments", []
                )
                stt_command.extend(
                    [
                        "--asr-train-command",
                        shlex.quote(" ".join(str(v) for v in train_command)),
                    ]
                )
            else:
                _LOGGER.warning("No speech to text training command was provided")

        return stt_command

    raise ValueError(f"Unsupported speech to text system (got {stt_system})")


def print_speech_to_text(
    stt_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for speech to text system"""
    stt_command = get_speech_to_text(
        stt_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    print("[program:speech_to_text]", file=out_file)
    print("command=", " ".join(stt_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for adapt, rasaNLU, flair


def get_intent_recognition(
    intent_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for intent recognition system"""
    dictionary_casing = profile.get("speech_to_text.dictionary_casing")

    if intent_system == "fsticuffs":
        graph = profile.get("intent.fsticuffs.intent_graph")
        assert graph, "Intent graph is required"

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
            "--intent-graph",
            shlex.quote(str(profile.write_path(graph))),
        ]

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        return intent_command

    if intent_system == "fuzzywuzzy":
        graph = profile.get("intent.fsticuffs.intent_graph")
        assert graph, "Intent graph is required"

        examples = profile.get("intent.fuzzywuzzy.examples_json")
        assert examples, "Examples JSON is required"

        intent_command = [
            "rhasspy-fuzzywuzzy-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--intent-graph",
            shlex.quote(str(profile.write_path(graph))),
            "--examples",
            shlex.quote(str(profile.write_path(examples))),
        ]

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        return intent_command

    if intent_system == "command":
        user_program = profile.get("intent.command.program")
        assert user_program
        user_command = [user_program] + profile.get("intent.command.arguments", [])

        intent_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--nlu-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        # Training
        intent_train_system = profile.get("training.intent.system", "auto")
        if intent_train_system == "auto":
            train_program = profile.get("training.intent.command.program")
            if train_program:
                train_command = [train_program] + profile.get(
                    "training.intent.command.arguments", []
                )
                intent_command.extend(
                    [
                        "--nlu-train-command",
                        shlex.quote(" ".join(str(v) for v in train_command)),
                    ]
                )
            else:
                _LOGGER.warning("No intent training command was provided")

        return intent_command

    if intent_system == "remote":
        url = profile.get("intent.remote.url")
        assert url, "intent.remote.url is required"

        intent_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--nlu-url",
            shlex.quote(url),
        ]

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        # Training
        intent_train_system = profile.get("training.intent.system", "auto")
        if intent_train_system == "auto":
            train_url = profile.get("training.intent.remote.url")
            if train_url:
                intent_command.extend(["--nlu-train-url", shlex.quote(train_url)])
            else:
                _LOGGER.warning("No intent training URL was provided")

        return intent_command

    raise ValueError(f"Unsupported intent recogniton system (got {intent_system})")


def print_intent_recognition(
    intent_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for intent recognition system"""
    intent_command = get_intent_recognition(
        intent_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:intent_recognition]", file=out_file)
    print("command=", " ".join(intent_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def get_intent_handling(
    handle_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Get command for intent handling system"""
    if handle_system == "hass":
        url = profile.get("home_assistant.url")
        assert url, "home_assistant.url is required"

        handle_command = [
            "rhasspy-homeassistant-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--url",
            shlex.quote(url),
        ]

        handle_type = profile.get("home_assistant.handle_type")
        if handle_type:
            handle_command.extend(["--handle-type", str(handle_type)])

        # Additional options
        access_token = profile.get("home_assistant.access_token")
        if access_token:
            handle_command.extend(["--access-token", str(access_token)])

        api_password = profile.get("home_assistant.api_password")
        if api_password:
            handle_command.extend(["--api-password", str(api_password)])

        event_type_format = profile.get("home_assistant.event_type_format")
        if event_type_format:
            handle_command.extend(["--event-type-format", str(event_type_format)])

        pem_file = profile.get("home_assistant.pem_file")
        if pem_file:
            handle_command.extend(["--pem-file", str(pem_file)])

        return handle_command

    if handle_system == "remote":
        url = profile.get("handle.remote.url")
        assert url, "handle.remote.url is required"

        handle_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--handle-url",
            shlex.quote(url),
        ]

        return handle_command

    if handle_system == "command":
        user_program = profile.get("handle.command.program")
        assert user_program, "handle.command.program is required"
        user_command = [user_program] + profile.get("handle.command.arguments", [])

        handle_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--handle-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        return handle_command

    raise ValueError(f"Unsupported intent handling system (got {handle_system})")


def print_intent_handling(
    handle_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for intent handling system"""
    handle_command = get_intent_handling(
        handle_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:intent_handling]", file=out_file)
    print("command=", " ".join(handle_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def get_dialogue(
    dialogue_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for dialogue management system"""
    if dialogue_system == "rhasspy":
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

        return dialogue_command

    raise ValueError(f"Unsupported dialogue system (got {dialogue_system})")


def print_dialogue(
    dialogue_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for dialogue management system"""
    dialogue_command = get_dialogue(
        dialogue_system,
        profile,
        siteId=siteId,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
    )

    print("[program:dialogue]", file=out_file)
    print("command=", " ".join(dialogue_command), sep="", file=out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for flite, picotts, MaryTTS, Google, NanoTTS


def get_text_to_speech(
    tts_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Get command for text to speech system"""
    if tts_system == "espeak":
        espeak_command = ["espeak", "--stdout"]
        voice = profile.get("text_to_speech.espeak.voice", "").strip()
        if not voice:
            voice = profile.get("language", "").strip()

        if voice:
            espeak_command.extend(["-v", str(voice)])

        espeak_command.extend(profile.get("text_to_speech.espeak.arguments", []))

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
            shlex.quote(" ".join(str(v) for v in espeak_command)),
        ]

        return tts_command

    if tts_system == "command":
        user_program = profile.get("text_to_speech.command.program")
        assert user_program, "text_to_speech.command.program is required"
        user_command = [user_program] + profile.get(
            "text_to_speech.command.arguments", []
        )

        tts_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        return tts_command

    if tts_system == "remote":
        url = profile.get("text_to_speech.remote.url")
        assert url, "text_to_speech.remote.url is required"

        tts_command = [
            "rhasspy-remote-http-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--tts-url",
            shlex.quote(url),
        ]

        return tts_command

    raise ValueError(f"Unsupported text to speech system (got {tts_system})")


def print_text_to_speech(
    tts_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for text to speech system"""
    tts_command = get_text_to_speech(
        tts_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:text_to_speech]", file=out_file)
    print("command=", " ".join(tts_command), sep="", file=out_file)


# -----------------------------------------------------------------------------


def get_speakers(
    sound_system: str,
    profile: Profile,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
) -> typing.List[str]:
    """Get command for audio output system"""
    if sound_system == "aplay":
        play_command = ["aplay", "-q", "-t", "wav"]
        list_command = ["aplay", "-L"]
        sound_device = profile.get("sounds.arecord.device", "").strip()
        if sound_device:
            play_command.extend(["-D", str(sound_device)])

        output_command = [
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
            "--list-command",
            shlex.quote(" ".join(list_command)),
        ]

        return output_command

    if sound_system == "command":
        # Command to play WAV files
        play_program = profile.get("sounds.command.play_program")
        assert play_program, "sounds.command.play_program is required"
        play_command = [play_program] + profile.get("sounds.command.play_arguments", [])

        output_command = [
            "rhasspy-speakers-cli-hermes",
            "--debug",
            "--siteId",
            str(siteId),
            "--host",
            str(mqtt_host),
            "--port",
            str(mqtt_port),
            "--play-command",
            shlex.quote(" ".join(str(v) for v in play_command)),
        ]

        # Command to list available audio output devices
        list_program = profile.get("sounds.command.list_program")
        if list_program:
            list_command = [list_program] + profile.get(
                "sounds.command.list_arguments", []
            )
            output_command.extend(
                ["--list-command", shlex.quote(" ".join(str(v) for v in list_command))]
            )
        else:
            _LOGGER.warning("No sound output device listing command provided.")

        return output_command

    raise ValueError(f"Unsupported sound output system (got {sound_system})")


def print_speakers(
    sound_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for audio output system"""
    output_command = get_speakers(
        sound_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )

    print("[program:speakers]", file=out_file)
    print("command=", " ".join(output_command), sep="", file=out_file)


# -----------------------------------------------------------------------------
# docker compose
# -----------------------------------------------------------------------------


def profile_to_docker(profile: Profile, out_file: typing.TextIO, local_mqtt_port=12183):
    """Transform Rhasspy profile to docker-compose.yml"""
    services: typing.Dict[str, typing.Any] = {}

    # MQTT
    siteId = str(profile.get("mqtt.site_id", "default"))
    mqtt_host = str(profile.get("mqtt.host", "localhost"))
    mqtt_port = int(profile.get("mqtt.port", 1883))

    # mqtt_username = str(profile.get("mqtt.username", "")).strip()
    # mqtt_password = str(profile.get("mqtt.password", "")).strip()

    remote_mqtt = profile.get("mqtt.enabled", False)
    if not remote_mqtt:
        # Use internal broker (mosquitto) on custom port
        mqtt_host = "mqtt"
        mqtt_host = local_mqtt_port
        compose_mqtt(services, mqtt_port=local_mqtt_port)

    # -------------------------------------------------------------------------

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system not in {"dummy", "hermes"}:
        compose_microphone(
            mic_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Microphone disabled (system=%s)", mic_system)

    # Speakers
    sound_system = profile.get("sounds.system", "dummy")
    if sound_system not in {"dummy", "hermes"}:
        compose_speakers(
            sound_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Speakers disabled (system=%s)", sound_system)

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if wake_system not in {"dummy", "hermes"}:
        compose_wake(
            wake_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Wake word disabled (system=%s)", wake_system)

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system not in {"dummy", "hermes"}:
        compose_speech_to_text(
            stt_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Speech to text disabled (system=%s)", stt_system)

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system not in {"dummy", "hermes"}:
        compose_intent_recognition(
            intent_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Intent recognition disabled (system=%s)", intent_system)

    # Text to Speech
    tts_system = profile.get("text_to_speech.system", "dummy")
    if tts_system not in {"dummy", "hermes"}:
        compose_text_to_speech(
            tts_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Text to speech disabled (system=%s)", tts_system)

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system not in {"dummy", "hermes"}:
        compose_dialogue(
            dialogue_system,
            profile,
            services,
            siteId=siteId,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )
    else:
        _LOGGER.debug("Dialogue disabled (system=%s)", dialogue_system)

    # Output
    yaml_dict = {"version": "2", "services": services}

    yaml.safe_dump(yaml_dict, out_file)


# -----------------------------------------------------------------------------


def compose_mqtt(services: typing.Dict[str, typing.Any], mqtt_port: int):
    """Print command for internal MQTT broker"""
    services["mqtt"] = {
        "image": "eclipse-mosquitto",
        "entrypoint": "mosquitto",
        "command": f"-p {mqtt_port}",
        "ports": [f"{mqtt_port}:{mqtt_port}"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_webserver(
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    mqtt_host: str,
    mqtt_port: int,
):
    """Print command for Rhasspy web server (http://localhost:12101)"""
    web_command = [
        "--host",
        "0.0.0.0",
        "--profile",
        profile.name,
        "--user-profiles",
        str(profile.user_profiles_dir),
        "--web-dir",
        "web",
        "--mqtt-host",
        str(mqtt_host),
        "--mqtt-port",
        str(mqtt_port),
    ]
    services["web"] = {
        "image": "rhasspy/rhasspy-server-hermes",
        "command": " ".join(web_command),
        "volumes": [f"{profile.user_profiles_dir}:{profile.user_profiles_dir}"],
        "ports": ["12101:12101"],
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_microphone(
    mic_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for microphone system"""
    mic_command = get_microphone(
        mic_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = mic_command.pop(0)

    services["microphone"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(mic_command),
        "devices": ["/dev/snd"],
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------

# TODO: Add support for precise


def compose_wake(
    wake_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for wake system"""
    wake_command = get_wake(
        wake_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = wake_command.pop(0)

    services["wake"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(wake_command),
        "volumes": [f"{profile.user_profiles_dir}:{profile.user_profiles_dir}"],
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_speech_to_text(
    stt_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for speech to text system"""
    stt_command = get_speech_to_text(
        stt_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = stt_command.pop(0)

    services["speech_to_text"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(stt_command),
        "volumes": [f"{profile.user_profiles_dir}:{profile.user_profiles_dir}"],
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_intent_recognition(
    intent_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for intent recognition system"""
    intent_command = get_intent_recognition(
        intent_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = intent_command.pop(0)

    services["intent_recognition"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(intent_command),
        "volumes": [f"{profile.user_profiles_dir}:{profile.user_profiles_dir}"],
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_dialogue(
    dialogue_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for dialogue management system"""
    dialogue_command = get_dialogue(
        dialogue_system,
        profile,
        siteId=siteId,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
    )
    service_name = dialogue_command.pop(0)

    services["dialogue"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(dialogue_command),
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_text_to_speech(
    tts_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for text to speech system"""
    tts_command = get_text_to_speech(
        tts_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = tts_command.pop(0)

    services["text_to_speech"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(tts_command),
        "depends_on": ["mqtt"],
        "tty": True,
    }


# -----------------------------------------------------------------------------


def compose_speakers(
    sound_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    siteId: str = "default",
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
):
    """Print command for audio output system"""
    output_command = get_speakers(
        sound_system, profile, siteId=siteId, mqtt_host=mqtt_host, mqtt_port=mqtt_port
    )
    service_name = output_command.pop(0)

    services["speakers"] = {
        "image": f"rhasspy/{service_name}",
        "command": " ".join(output_command),
        "devices": ["/dev/snd"],
        "depends_on": ["mqtt"],
        "tty": True,
    }
