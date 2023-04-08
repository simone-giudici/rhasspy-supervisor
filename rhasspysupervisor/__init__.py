"""Tools for generating supervisord/docker files for Rhasspy"""
import itertools
import logging
import os
import shlex
import shutil
import typing
from pathlib import Path
from urllib.parse import urljoin

import yaml
from rhasspyprofile import Profile

_LOGGER = logging.getLogger("rhasspysupervisor")

# -----------------------------------------------------------------------------
# supervisord
# -----------------------------------------------------------------------------


def profile_to_conf(
    profile: Profile,
    out_file: typing.TextIO,
    local_mqtt_port=12183,
    mosquitto_path="mosquitto",
):
    """Generate supervisord conf from Rhasspy profile"""

    # Header
    print("[supervisord]", file=out_file)
    print("nodaemon=true", file=out_file)
    print("", file=out_file)

    # MQTT
    master_site_ids = str(profile.get("mqtt.site_id", "default")).split(",")

    mqtt_host = str(profile.get("mqtt.host", "localhost"))

    try:
        mqtt_port = int(profile.get("mqtt.port", 1883))
    except ValueError:
        mqtt_port = 1883

    mqtt_username = str(profile.get("mqtt.username", "")).strip()
    mqtt_password = str(profile.get("mqtt.password", "")).strip()

    remote_mqtt = str(profile.get("mqtt.enabled", False)).lower() == "true"
    if not remote_mqtt:
        # Use internal broker (mosquitto) on custom port
        mqtt_host = "localhost"
        mqtt_port = local_mqtt_port
        mqtt_username = ""
        mqtt_password = ""
        print_mqtt(out_file, mqtt_port=local_mqtt_port, mosquitto_path=mosquitto_path)

    # -------------------------------------------------------------------------

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("microphone.satellite_site_ids", "")
        ).split(",")
        print_microphone(
            mic_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Microphone disabled (system=%s)", mic_system)

    # Speakers
    sound_system = profile.get("sounds.system", "dummy")
    if sound_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("sounds.satellite_site_ids", "")).split(
            ","
        )
        print_speakers(
            sound_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Speakers disabled (system=%s)", sound_system)

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if wake_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("wake.satellite_site_ids", "")).split(",")
        print_wake(
            wake_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Wake word disabled (system=%s)", wake_system)

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("speech_to_text.satellite_site_ids", "")
        ).split(",")
        print_speech_to_text(
            stt_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Speech to text disabled (system=%s)", stt_system)

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("intent.satellite_site_ids", "")).split(
            ","
        )
        print_intent_recognition(
            intent_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Intent recognition disabled (system=%s)", intent_system)

    # Intent Handling
    handle_system = profile.get("handle.system", "dummy")
    if handle_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("handle.satellite_site_ids", "")).split(
            ","
        )
        print_intent_handling(
            handle_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Intent handling disabled (system=%s)", handle_system)

    # Text to Speech
    tts_system = profile.get("text_to_speech.system", "dummy")
    if tts_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("text_to_speech.satellite_site_ids", "")
        ).split(",")
        print_text_to_speech(
            tts_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Text to speech disabled (system=%s)", tts_system)

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("dialogue.satellite_site_ids", "")).split(
            ","
        )
        print_dialogue(
            dialogue_system,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            master_site_ids=master_site_ids,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Dialogue disabled (system=%s)", dialogue_system)

    # Webhooks
    webhooks = profile.get("webhooks", {})
    webhook_events = [k for k in webhooks.keys() if k != "satellite_site_ids"]
    if webhook_events:
        satellite_site_ids = str(profile.get("webhooks.satellite_site_ids", "")).split(
            ","
        )
        print_webhooks(
            webhooks,
            profile,
            out_file,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )


def write_boilerplate(out_file: typing.TextIO):
    """Write boilerplate settings for supervisord service"""
    print("stopasgroup=true", file=out_file)
    print("stdout_logfile=/dev/stdout", file=out_file)
    print("stdout_logfile_maxbytes=0", file=out_file)
    print("redirect_stderr=true", file=out_file)
    print("", file=out_file)


# -----------------------------------------------------------------------------


def print_mqtt(out_file: typing.TextIO, mqtt_port: int, mosquitto_path="mosquitto"):
    """Print command for internal MQTT broker"""
    mqtt_command = [mosquitto_path, "-p", str(mqtt_port)]

    if mqtt_command:
        print("[program:mqtt]", file=out_file)
        print("command=", " ".join(mqtt_command), sep="", file=out_file)

        # Ensure broker starts first
        print("priority=0", file=out_file)

        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def add_standard_args(
    profile: Profile,
    command: typing.List[str],
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Add typical MQTT arguments to a command."""
    command.append("--debug")

    command.extend(["--host", str(mqtt_host)])
    command.extend(["--port", str(mqtt_port)])

    for site_id in site_ids:
        site_id = site_id.strip()
        if site_id:
            command.extend(["--site-id", shlex.quote(str(site_id))])

    if mqtt_username:
        command.extend(["--username", shlex.quote(str(mqtt_username))])
        command.extend(["--password", shlex.quote(str(mqtt_password))])

    # TLS
    tls_enabled = profile.get("mqtt.tls.enabled", False)
    if tls_enabled:
        command.append("--tls")

        # Certificate Authority certs
        tls_ca_certs = profile.get("mqtt.tls.ca_certs")
        if tls_ca_certs:
            command.extend(["--tls-ca-certs", shlex.quote(str(tls_ca_certs))])

        # CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE
        tls_cert_reqs = profile.get("mqtt.tls.cert_reqs")
        if tls_cert_reqs:
            command.extend(["--tls-cert-reqs", shlex.quote(str(tls_cert_reqs))])

        # PEM
        tls_certfile = profile.get("mqtt.tls.certfile")
        if tls_certfile:
            command.extend(["--tls-certfile", shlex.quote(str(tls_certfile))])

        tls_keyfile = profile.get("mqtt.tls.keyfile")
        if tls_keyfile:
            command.extend(["--tls-keyfile", shlex.quote(str(tls_keyfile))])

        # Cipers/version
        tls_ciphers = profile.get("mqtt.tls.ciphers")
        if tls_ciphers:
            command.extend(["--tls-ciphers", shlex.quote(str(tls_ciphers))])

        tls_version = profile.get("mqtt.tls.version")
        if tls_version:
            command.extend(["--tls-version", shlex.quote(str(tls_version))])

    log_format = profile.get("logging.format", "")
    if log_format:
        command.extend(["--log-format", shlex.quote(str(log_format))])


def add_lang_args(profile: Profile, command: typing.List[str], system_type: str):
    """Add --lang to service for setting language in messages"""
    maybe_lang = profile.get(f"{system_type}.lang")
    if maybe_lang:
        command.extend(["--lang", str(maybe_lang)])


# -----------------------------------------------------------------------------

# TODO: Add chunk sizes


def get_microphone(
    mic_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
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

        add_standard_args(
            profile,
            mic_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        udp_audio_host = profile.get("microphone.arecord.udp_audio_host", "127.0.0.1")
        if udp_audio_host:
            mic_command.extend(["--udp-audio-host", str(udp_audio_host)])

        udp_audio_port = profile.get("microphone.arecord.udp_audio_port", "")
        if udp_audio_port:
            mic_command.extend(["--udp-audio-port", str(udp_audio_port)])

        output_site_id = profile.get("microphone.arecord.site_id", "")
        if output_site_id:
            mic_command.extend(["--output-site-id", shlex.quote(str(output_site_id))])

        return mic_command

    if mic_system == "pyaudio":
        mic_command = [
            "rhasspy-microphone-pyaudio-hermes",
            "--sample-rate",
            "16000",
            "--sample-width",
            "2",
            "--channels",
            "1",
        ]

        add_standard_args(
            profile,
            mic_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        mic_device = profile.get("microphone.pyaudio.device", "").strip()
        if mic_device:
            mic_command.extend(["--device-index", str(mic_device)])

        output_site_id = profile.get("microphone.pyaudio.site_id", "")
        if output_site_id:
            mic_command.extend(["--output-site-id", shlex.quote(str(output_site_id))])

        udp_audio_host = profile.get("microphone.pyaudio.udp_audio_host", "127.0.0.1")
        if udp_audio_host:
            mic_command.extend(["--udp-audio-host", str(udp_audio_host)])

        udp_audio_port = profile.get("microphone.pyaudio.udp_audio_port", "")
        if udp_audio_port:
            mic_command.extend(["--udp-audio-port", str(udp_audio_port)])

        frames_per_buffer = profile.get("microphone.pyaudio.frames_per_buffer")
        if frames_per_buffer is not None:
            mic_command.extend(["--frames-per-buffer", str(frames_per_buffer)])

        return mic_command

    if mic_system == "command":
        # Command to record audio
        record_program = profile.get("microphone.command.record_program")
        if not record_program:
            _LOGGER.error("microphone.command.record_program is required")
            return []

        record_command = [record_program] + command_args(
            profile.get("microphone.command.record_arguments", [])
        )

        sample_rate = int(profile.get("microphone.command.sample_rate", 16000))
        sample_width = int(profile.get("microphone.command.sample_width", 2))
        channels = int(profile.get("microphone.command.channels", 1))

        mic_command = [
            "rhasspy-microphone-cli-hermes",
            "--sample-rate",
            str(sample_rate),
            "--sample-width",
            str(sample_width),
            "--channels",
            str(channels),
            "--record-command",
            shlex.quote(" ".join(record_command)),
        ]

        add_standard_args(
            profile,
            mic_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

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

        # UDP/output site_id
        udp_audio_port = profile.get("microphone.command.udp_audio_port", "")
        if udp_audio_port:
            mic_command.extend(["--udp-audio-port", str(udp_audio_port)])

        output_site_id = profile.get("microphone.command.site_id", "")
        if output_site_id:
            mic_command.extend(["--output-site-id", shlex.quote(str(output_site_id))])

        return mic_command

    raise ValueError(f"Unsupported audio input system (got {mic_system})")


def print_microphone(
    mic_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for microphone system"""
    mic_command = get_microphone(
        mic_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if mic_command:
        print("[program:microphone]", file=out_file)
        print("command=", " ".join(mic_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def get_wake(
    wake_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for wake system"""
    wake_site_id = "default" if not site_ids else site_ids[0]

    if wake_system == "porcupine":
        keyword = profile.get("wake.porcupine.keyword_path") or "porcupine.ppn"
        if not keyword:
            _LOGGER.error("wake.porcupine.keyword_path required")
            return []

        sensitivity = profile.get("wake.porcupine.sensitivity", "0.5")
        access_key = profile.get("wake.porcupine.access_key")

        wake_command = [
            "rhasspy-wake-porcupine-hermes",
            "--keyword",
            shlex.quote(str(keyword)),
            "--sensitivity",
            str(sensitivity),
            "--access-key",
            str(access_key),
            "--keyword-dir",
            shlex.quote(str(write_path(profile, "porcupine"))),
        ]

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

        udp_audio = profile.get("wake.porcupine.udp_audio", "")
        if udp_audio:
            udp_site_info = profile.get("wake.porcupine.udp_site_info", {})
            add_udp_audio_settings(wake_command, udp_audio, wake_site_id, udp_site_info)

        return wake_command

    if wake_system == "snowboy":
        wake_command = [
            "rhasspy-wake-snowboy-hermes",
            "--model-dir",
            shlex.quote(str(write_path(profile, "snowboy"))),
        ]

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

        udp_audio = profile.get("wake.snowboy.udp_audio", "")
        if udp_audio:
            udp_site_info = profile.get("wake.snowboy.udp_site_info", {})
            add_udp_audio_settings(wake_command, udp_audio, wake_site_id, udp_site_info)

        # Default settings
        sensitivity = str(profile.get("wake.snowboy.sensitivity", "0.5"))
        audio_gain = float(profile.get("wake.snowboy.audio_gain", "1.0"))
        apply_frontend = bool(profile.get("wake.snowboy.apply_frontend", False))

        model_names: typing.List[str] = (
            profile.get("wake.snowboy.model") or "snowboy.umdl"
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

            model_args = [
                shlex.quote(str(model_name)),
                str(settings["sensitivity"]),
                str(settings["audio_gain"]),
                str(settings["apply_frontend"]),
            ]
            wake_command.extend(["--model"] + model_args)

        return wake_command

    if wake_system == "precise":
        model = profile.get("wake.precise.model") or "hey-mycroft-2.pb"
        if not model:
            _LOGGER.error("wake.precise.model required")
            return []

        sensitivity = str(profile.get("wake.precise.sensitivity", 0.5)) or "0.5"
        trigger_level = str(profile.get("wake.precise.trigger_level", 3)) or "3"

        wake_command = [
            "rhasspy-wake-precise-hermes",
            "--model",
            shlex.quote(str(model)),
            "--sensitivity",
            str(sensitivity),
            "--trigger-level",
            str(trigger_level),
            "--model-dir",
            shlex.quote(str(write_path(profile, "precise"))),
        ]

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

        udp_audio = profile.get("wake.precise.udp_audio", "")
        if udp_audio:
            udp_site_info = profile.get("wake.porcupine.udp_site_info", {})
            add_udp_audio_settings(wake_command, udp_audio, wake_site_id, udp_site_info)

        return wake_command

    if wake_system == "pocketsphinx":
        # Load decoder settings (use speech-to-text configuration as a fallback)
        acoustic_model = profile.get("wake.pocketsphinx.acoustic_model") or profile.get(
            "speech_to_text.pocketsphinx.acoustic_model"
        )
        if not acoustic_model:
            _LOGGER.error("acoustic model required")
            return []

        dictionaries = [
            profile.get("wake.pocketsphinx.dictionary"),
            profile.get("speech_to_text.pocketsphinx.base_dictionary"),
            profile.get("speech_to_text.pocketsphinx.dictionary"),
            profile.get("speech_to_text.pocketsphinx.custom_words"),
        ]

        wake_command = [
            "rhasspy-wake-pocketsphinx-hermes",
            "--keyphrase",
            shlex.quote(str(profile.get("wake.pocketsphinx.keyphrase", "okay raspy"))),
            "--keyphrase-threshold",
            str(profile.get("wake.pocketsphinx.threshold", "1e-40")),
            "--acoustic-model",
            shlex.quote(str(write_path(profile, acoustic_model))),
        ]

        for dictionary in dictionaries:
            if dictionary:
                wake_command.extend(
                    ["--dictionary", shlex.quote(str(write_path(profile, dictionary)))]
                )

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

        udp_audio = profile.get("wake.pocketsphinx.udp_audio", "")
        if udp_audio:
            udp_site_info = profile.get("wake.pocketsphinx.udp_site_info", {})
            add_udp_audio_settings(wake_command, udp_audio, wake_site_id, udp_site_info)

        mllr_matrix = profile.get("wake.pocketsphinx.mllr_matrix")
        if mllr_matrix:
            wake_command.extend(
                ["--mllr-matrix", shlex.quote(str(write_path(profile, mllr_matrix)))]
            )

        return wake_command

    if wake_system == "raven":
        wake_command = ["rhasspy-wake-raven-hermes"]

        template_dir = profile.get("wake.raven.template_dir", "raven")
        if not template_dir:
            _LOGGER.error("wake.raven.template_dir is required")
            return []

        keywords = profile.get("wake.raven.keywords", {})

        # Try to automatically detect keywords
        keywords_dir = write_path(profile, template_dir)
        if keywords_dir.is_dir():
            for keyword_dir in keywords_dir.iterdir():
                if keyword_dir.is_dir() and (keyword_dir.name not in keywords):
                    keywords[keyword_dir.name] = {"enabled": True}

        for keyword_dir_name, keyword_settings in keywords.items():
            if not keyword_settings.get("enabled", True):
                continue

            # Exclude keywords whose directory doesn't exist
            keyword_dir = keywords_dir / keyword_dir_name
            if not keyword_dir.is_dir():
                continue

            # Add keyword as a directory relative to the template dir
            wake_command.extend(
                [
                    "--keyword",
                    shlex.quote(
                        str(write_path(profile, template_dir, keyword_dir_name))
                    ),
                ]
            )

            # Override settings for specific keyword
            for setting_name, setting_value in keyword_settings.items():
                wake_command.append(shlex.quote(f"{setting_name}={setting_value}"))

        probability_threshold = profile.get("wake.raven.probability_threshold")
        if probability_threshold:
            wake_command.extend(["--probability-threshold", str(probability_threshold)])

        minimum_matches = profile.get("wake.raven.minimum_matches")
        if minimum_matches:
            wake_command.extend(["--minimum-matches", str(minimum_matches)])

        average_templates = profile.get("wake.raven.average_templates", True)
        if average_templates:
            wake_command.append("--average-templates")

        vad_sensitivity = profile.get("wake.raven.vad_sensitivity", 1)
        if vad_sensitivity:
            wake_command.extend(["--vad-sensitivity", str(vad_sensitivity)])

        # Positive examples
        examples_dir = profile.get("wake.raven.examples_dir")
        if examples_dir:
            wake_command.extend(
                ["--examples-dir", shlex.quote(str(write_path(profile, examples_dir)))]
            )

        examples_format = profile.get("wake.raven.examples_format")
        if examples_format:
            wake_command.extend(
                ["--examples-format", shlex.quote(str(examples_format))]
            )

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

        udp_audio = profile.get("wake.raven.udp_audio", "")
        if udp_audio:
            udp_site_info = profile.get("wake.pocketsphinx.udp_site_info", {})
            add_udp_audio_settings(wake_command, udp_audio, wake_site_id, udp_site_info)

        return wake_command

    if wake_system == "command":
        user_program = profile.get("wake.command.program")
        if not user_program:
            _LOGGER.error("wake.command.program is required")
            return []

        user_command = [user_program] + command_args(
            profile.get("wake.command.arguments", [])
        )

        wake_command = [
            "rhasspy-remote-http-hermes",
            "--wake-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        add_standard_args(
            profile,
            wake_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, wake_command, "wake")

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

        add_ssl_args(wake_command, profile)

        return wake_command

    raise ValueError(f"Unsupported wake system (got {wake_system})")


def print_wake(
    wake_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for wake system"""
    wake_command = get_wake(
        wake_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if wake_command:
        print("[program:wake_word]", file=out_file)
        print("command=", " ".join(wake_command), sep="", file=out_file)
        write_boilerplate(out_file)


def add_udp_audio_settings(
    command: typing.List[str],
    udp_audio: str,
    site_id: str,
    udp_site_info: typing.Optional[typing.Dict[str, typing.Any]] = None,
):
    """Parse UDP audio settings."""

    # Comma-separated list of host:port:siteId
    for udp_settings_str in udp_audio.split(","):
        udp_settings = udp_settings_str.split(":")
        udp_host = "127.0.0.1"
        udp_port: typing.Optional[int] = None
        udp_site_id = site_id

        if len(udp_settings) == 1:
            # Port only
            udp_port = int(udp_settings[0])
        elif len(udp_settings) == 2:
            # Host/port only
            udp_host = udp_settings[0]
            udp_port = int(udp_settings[1])
        elif len(udp_settings) > 2:
            # Host/port/siteId
            udp_host = udp_settings[0]
            udp_port = int(udp_settings[1])
            udp_site_id = udp_settings[2]

        assert udp_port is not None, "No UDP port"

        # Add to command
        command.extend(
            [
                "--udp-audio",
                shlex.quote(udp_host),
                str(udp_port),
                shlex.quote(udp_site_id),
            ]
        )

        udp_site_info = udp_site_info or {}
        for udp_site_id, site_info in udp_site_info.items():
            if site_info.get("raw_audio", False):
                # UDP audio is raw PCM instead of WAV chunks
                command.extend(["--udp-raw-audio", str(udp_site_id)])

            if site_info.get("forward_to_mqtt", False):
                # UDP audio should be forwarded to MQTT after detection
                command.extend(["--udp-forward-mqtt", str(udp_site_id)])


# -----------------------------------------------------------------------------


def get_speech_to_text(
    stt_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for speech to text system"""
    if stt_system == "pocketsphinx":
        # Pocketsphinx
        acoustic_model = profile.get("speech_to_text.pocketsphinx.acoustic_model")
        if not acoustic_model:
            _LOGGER.error("speech_to_text.pocketsphinx.acoustic_model is required")
            return []

        # Open transcription
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

        if not dictionary:
            _LOGGER.error("Pocketsphinx dictionary is required")
            return []

        if not language_model:
            _LOGGER.error("Pocketsphinx language model required")
            return []

        stt_command = [
            "rhasspy-asr-pocketsphinx-hermes",
            "--acoustic-model",
            shlex.quote(str(write_path(profile, acoustic_model))),
            "--dictionary",
            shlex.quote(str(write_path(profile, dictionary))),
            "--language-model",
            shlex.quote(str(write_path(profile, language_model))),
        ]

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        graph = profile.get("intent.fsticuffs.intent_graph")
        if graph:
            # Path to intent graph
            stt_command.extend(
                ["--intent-graph", shlex.quote(str(write_path(profile, graph)))]
            )

        if open_transcription:
            # Don't overwrite dictionary or language model during training
            stt_command.append("--no-overwrite-train")

        base_dictionary = profile.get("speech_to_text.pocketsphinx.base_dictionary")
        if base_dictionary:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(write_path(profile, base_dictionary))),
                ]
            )

        custom_words = profile.get("speech_to_text.pocketsphinx.custom_words")
        if custom_words:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(write_path(profile, custom_words))),
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
                ["--g2p-model", shlex.quote(str(write_path(profile, g2p_model)))]
            )

        # Case transformation for grapheme-to-phoneme model
        g2p_casing = profile.get("speech_to_text.g2p_casing")
        if g2p_casing:
            stt_command.extend(["--g2p-casing", g2p_casing])

        # Path to write missing words and guessed pronunciations
        unknown_words = profile.get("speech_to_text.pocketsphinx.unknown_words")
        if unknown_words:
            stt_command.extend(
                [
                    "--unknown-words",
                    shlex.quote(str(write_path(profile, unknown_words))),
                ]
            )

        # Mixed language model
        base_lm_fst = profile.get("speech_to_text.pocketsphinx.base_language_model_fst")
        if base_lm_fst:
            stt_command.extend(
                [
                    "--base-language-model-fst",
                    shlex.quote(str(write_path(profile, base_lm_fst))),
                ]
            )

        base_lm_weight = str(profile.get("speech_to_text.pocketsphinx.mix_weight", ""))
        if base_lm_weight:
            stt_command.extend(["--base-language-model-weight", str(base_lm_weight)])

        mix_lm_fst = profile.get("speech_to_text.pocketsphinx.mix_fst")
        if mix_lm_fst:
            stt_command.extend(
                [
                    "--mixed-language-model-fst",
                    shlex.quote(str(write_path(profile, mix_lm_fst))),
                ]
            )

        # Silence detection
        add_silence_args(stt_command, profile)

        return stt_command

    if stt_system == "kaldi":
        # Kaldi
        model_dir = profile.get("speech_to_text.kaldi.model_dir")
        if not model_dir:
            _LOGGER.error("speech_to_text.kaldi.model_dir is required")
            return []

        model_dir = write_path(profile, model_dir)

        # Open transcription
        open_transcription = bool(
            profile.get("speech_to_text.kaldi.open_transcription", False)
        )

        if open_transcription:
            graph = profile.get("speech_to_text.kaldi.base_graph")
        else:
            graph = profile.get("speech_to_text.kaldi.graph")

        if not graph:
            _LOGGER.error("Kaldi graph directory is required")
            return []

        graph = model_dir / graph

        model_type = profile.get("speech_to_text.kaldi.model_type")
        if not model_type:
            _LOGGER.error("Kaldi model type is required")
            return []

        stt_command = [
            "rhasspy-asr-kaldi-hermes",
            "--model-type",
            str(model_type),
            "--model-dir",
            shlex.quote(str(model_dir)),
            "--graph-dir",
            shlex.quote(str(graph)),
        ]

        # Spoken noise phone (SPN for <unk>)
        spn_phone = profile.get("speech_to_text.kaldi.spn_phone")
        if spn_phone:
            stt_command.extend(["--spn-phone", str(spn_phone)])

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        if open_transcription:
            # Don't overwrite HCLG.fst during training
            stt_command.append("--no-overwrite-train")
        else:
            dictionary = profile.get("speech_to_text.kaldi.dictionary")
            if dictionary:
                stt_command.extend(
                    ["--dictionary", shlex.quote(str(write_path(profile, dictionary)))]
                )

            language_model = profile.get("speech_to_text.kaldi.language_model")
            if language_model:
                stt_command.extend(
                    [
                        "--language-model",
                        shlex.quote(str(write_path(profile, language_model))),
                    ]
                )

            # ARPA or text FST (G.fst)
            language_model_type = profile.get(
                "speech_to_text.kaldi.language_model_type"
            )
            if language_model_type:
                stt_command.extend(["--language-model-type", str(language_model_type)])

        base_dictionary = profile.get("speech_to_text.kaldi.base_dictionary")
        if base_dictionary:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(write_path(profile, base_dictionary))),
                ]
            )

        custom_words = profile.get("speech_to_text.kaldi.custom_words")
        if custom_words:
            stt_command.extend(
                [
                    "--base-dictionary",
                    shlex.quote(str(write_path(profile, custom_words))),
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
                ["--g2p-model", shlex.quote(str(write_path(profile, g2p_model)))]
            )

        # Case transformation for grapheme-to-phoneme model
        g2p_casing = profile.get("speech_to_text.g2p_casing")
        if g2p_casing:
            stt_command.extend(["--g2p-casing", g2p_casing])

        # Path to write missing words and guessed pronunciations
        unknown_words = profile.get("speech_to_text.kaldi.unknown_words")
        if unknown_words:
            stt_command.extend(
                [
                    "--unknown-words",
                    shlex.quote(str(write_path(profile, unknown_words))),
                ]
            )

        # Mixed language model
        base_lm_fst = profile.get("speech_to_text.kaldi.base_language_model_fst")
        if base_lm_fst:
            stt_command.extend(
                [
                    "--base-language-model-fst",
                    shlex.quote(str(write_path(profile, base_lm_fst))),
                ]
            )

        base_lm_weight = str(profile.get("speech_to_text.kaldi.mix_weight", ""))
        if base_lm_weight:
            stt_command.extend(["--base-language-model-weight", str(base_lm_weight)])

        mix_lm_fst = profile.get("speech_to_text.kaldi.mix_fst")
        if mix_lm_fst:
            stt_command.extend(
                [
                    "--mixed-language-model-fst",
                    shlex.quote(str(write_path(profile, mix_lm_fst))),
                ]
            )

        # Unknown words
        frequent_words = profile.get("speech_to_text.kaldi.frequent_words")
        if frequent_words:
            stt_command.extend(
                [
                    "--frequent-words",
                    shlex.quote(str(profile.read_path(frequent_words))),
                ]
            )

        max_frequent_words = profile.get("speech_to_text.kaldi.max_frequent_words")
        if max_frequent_words:
            stt_command.extend(
                ["--max-frequent-words", shlex.quote(str(max_frequent_words))]
            )

        max_unknown_words = profile.get("speech_to_text.kaldi.max_unknown_words")
        if max_unknown_words:
            stt_command.extend(
                ["--max-unknown-words", shlex.quote(str(max_unknown_words))]
            )

        if profile.get("speech_to_text.kaldi.allow_unknown_words", False):
            stt_command.append("--allow-unknown-words")

        unknown_words_probability = profile.get(
            "speech_to_text.kaldi.unknown_words_probability"
        )
        if unknown_words_probability is not None:
            stt_command.extend(
                [
                    "--unknown-words-probability",
                    shlex.quote(str(unknown_words_probability)),
                ]
            )

        unknown_token = profile.get("speech_to_text.kaldi.unknown_token")
        if unknown_token is not None:
            stt_command.extend(["--unknown-token", shlex.quote(str(unknown_token))])

        silence_probability = profile.get("speech_to_text.kaldi.silence_probability")
        if silence_probability is not None:
            stt_command.extend(
                ["--silence-probability", shlex.quote(str(silence_probability))]
            )

        cancel_word = profile.get("speech_to_text.kaldi.cancel_word")
        if cancel_word is not None:
            stt_command.extend(["--cancel-word", shlex.quote(str(cancel_word))])

        cancel_probability = profile.get("speech_to_text.kaldi.cancel_probability")
        if cancel_probability is not None:
            stt_command.extend(
                ["--cancel-probability", shlex.quote(str(cancel_probability))]
            )

        # Silence detection
        add_silence_args(stt_command, profile)

        return stt_command

    if stt_system == "vosk":
        # Vosk
        model_dir = profile.get("speech_to_text.vosk.model_dir")
        if not model_dir:
            _LOGGER.error("speech_to_text.vosk.model_dir is required")
            return []

        model_dir = write_path(profile, model_dir)

        # Open transcription
        open_transcription = bool(
            profile.get("speech_to_text.vosk.open_transcription", False)
        )

        stt_command = ["rhasspy-asr-vosk-hermes", "--model", str(model_dir)]

        if open_transcription:
            # Don't overwrite words JSON during training
            stt_command.append("--no-overwrite-train")
        else:
            # Create lists of valid words from training sentences
            words_json_path = profile.get(
                "speech_to_text.vosk.words_json", "vosk/words.json"
            )
            stt_command.extend(
                ["--words-json", shlex.quote(str(write_path(profile, words_json_path)))]
            )

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        return stt_command

    if stt_system == "command":
        user_program = profile.get("speech_to_text.command.program")
        if not user_program:
            _LOGGER.error("speech_to_text.command.program is required")
            return []

        user_command = [user_program] + command_args(
            profile.get("speech_to_text.command.arguments", [])
        )

        stt_command = [
            "rhasspy-remote-http-hermes",
            "--asr-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        add_ssl_args(stt_command, profile)

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
        if not url:
            _LOGGER.error("speech_to_text.remote.url is required")
            return []

        stt_command = ["rhasspy-remote-http-hermes", "--asr-url", shlex.quote(url)]

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        add_ssl_args(stt_command, profile)

        # Training
        stt_train_system = profile.get("training.speech_to_text.system", "auto")
        if stt_train_system == "auto":
            train_url = profile.get("training.speech_to_text.remote.url")
            if train_url:
                stt_command.extend(["--asr-train-url", shlex.quote(str(train_url))])
            else:
                _LOGGER.warning("No speech to text training URL was provided")

        # Silence detection
        add_silence_args(stt_command, profile)

        return stt_command

    if stt_system == "deepspeech":
        # DeepSpeech
        acoustic_model = profile.get("speech_to_text.deepspeech.acoustic_model")
        if not acoustic_model:
            _LOGGER.error("speech_to_text.deepspeech.acoustic_model is required")
            return []

        # Open transcription
        open_transcription = bool(
            profile.get("speech_to_text.deepspeech.open_transcription", False)
        )

        if open_transcription:
            language_model = profile.get(
                "speech_to_text.deepspeech.base_language_model"
            )
            scorer = profile.get("speech_to_text.deepspeech.base_scorer")
        else:
            language_model = profile.get("speech_to_text.deepspeech.language_model")
            scorer = profile.get("speech_to_text.deepspeech.scorer")

        if not language_model:
            _LOGGER.error("DeepSpeech language model required")
            return []

        if not scorer:
            _LOGGER.error("DeepSpeech scorer is required")
            return []

        alphabet = profile.get("speech_to_text.deepspeech.alphabet")
        if not alphabet:
            _LOGGER.error("DeepSpeech alphabet is required")
            return []

        stt_command = [
            "rhasspy-asr-deepspeech-hermes",
            "--model",
            shlex.quote(str(write_path(profile, acoustic_model))),
            "--language-model",
            shlex.quote(str(write_path(profile, language_model))),
            "--scorer",
            shlex.quote(str(write_path(profile, scorer))),
            "--alphabet",
            shlex.quote(str(write_path(profile, alphabet))),
        ]

        add_standard_args(
            profile,
            stt_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, stt_command, "speech_to_text")

        if open_transcription:
            # Don't overwrite dictionary or language model during training
            stt_command.append("--no-overwrite-train")

        # Mixed language model
        base_lm_fst = profile.get("speech_to_text.deepspeech.base_language_model_fst")
        if base_lm_fst:
            stt_command.extend(
                [
                    "--base-language-model-fst",
                    shlex.quote(str(write_path(profile, base_lm_fst))),
                ]
            )

        base_lm_weight = str(profile.get("speech_to_text.deepspeech.mix_weight", ""))
        if base_lm_weight:
            stt_command.extend(["--base-language-model-weight", str(base_lm_weight)])

        mix_lm_fst = profile.get("speech_to_text.deepspeech.mix_fst")
        if mix_lm_fst:
            stt_command.extend(
                [
                    "--mixed-language-model-fst",
                    shlex.quote(str(write_path(profile, mix_lm_fst))),
                ]
            )

        lm_alpha = str(profile.get("speech_to_text.deepspeech.lm_alpha", ""))
        if lm_alpha:
            stt_command.extend(["--lm-alpha", lm_alpha])

        lm_beta = str(profile.get("speech_to_text.deepspeech.lm_beta", ""))
        if lm_beta:
            stt_command.extend(["--lm-beta", lm_beta])

        # Silence detection
        add_silence_args(stt_command, profile)

        return stt_command

    raise ValueError(f"Unsupported speech to text system (got {stt_system})")


def print_speech_to_text(
    stt_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for speech to text system"""
    stt_command = get_speech_to_text(
        stt_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if stt_command:
        print("[program:speech_to_text]", file=out_file)
        print("command=", " ".join(stt_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for adapt, flair


def get_intent_recognition(
    intent_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for intent recognition system"""
    dictionary_casing = profile.get("speech_to_text.dictionary_casing")

    if intent_system == "fsticuffs":
        graph = profile.get("intent.fsticuffs.intent_graph")
        if not graph:
            _LOGGER.error("intent.fsticuffs.intent_graph is required")
            return []

        intent_command = [
            "rhasspy-nlu-hermes",
            "--intent-graph",
            shlex.quote(str(write_path(profile, graph))),
        ]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, intent_command, "intent")

        fuzzy = profile.get("intent.fsticuffs.fuzzy", True)
        if not fuzzy:
            intent_command.append("--no-fuzzy")

        replace_numbers = profile.get("intent.replace_numbers", True)
        if replace_numbers:
            intent_command.append("--replace-numbers")

            locale = profile.get("locale")
            if locale:
                intent_command.extend(["--language", str(locale)])

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        # Directory with custom converter scripts
        converters_dir = profile.get("intent.fsticuffs.converters_dir", "converters")
        intent_command.extend(
            ["--converters-dir", shlex.quote(str(write_path(profile, converters_dir)))]
        )

        failure_token = profile.get("intent.fsticuffs.failure_token", "<unk>")
        if failure_token:
            intent_command.extend(["--failure-token", str(failure_token)])

        return intent_command

    if intent_system == "fuzzywuzzy":
        graph = profile.get("intent.fsticuffs.intent_graph")
        if not graph:
            _LOGGER.error("intent.fsticuffs.intent_graph is required")
            return []

        examples = profile.get("intent.fuzzywuzzy.examples_json")
        if not examples:
            _LOGGER.error("intent.fuzzywuzzy.examples_json is required")
            return []

        intent_command = [
            "rhasspy-fuzzywuzzy-hermes",
            "--intent-graph",
            shlex.quote(str(write_path(profile, graph))),
            "--examples",
            shlex.quote(str(write_path(profile, examples))),
        ]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, intent_command, "intent")

        confidence_threshold = profile.get("intent.fuzzywuzzy.min_confidence")
        if confidence_threshold is not None:
            intent_command.extend(["--confidence-threshold", str(confidence_threshold)])

        replace_numbers = profile.get("intent.replace_numbers", True)
        if replace_numbers:
            intent_command.append("--replace-numbers")

            locale = profile.get("locale")
            if locale:
                intent_command.extend(["--language", str(locale)])

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        # Directory with custom converter scripts
        converters_dir = profile.get("intent.fuzzywuzzy.converters_dir", "converters")
        intent_command.extend(
            ["--converters-dir", shlex.quote(str(write_path(profile, converters_dir)))]
        )

        return intent_command

    if intent_system == "rasa":
        url = profile.get("intent.rasa.url", "")
        if not url:
            _LOGGER.error("intent.rasa.url is required")
            return []

        intent_command = [
            "rhasspy-rasa-nlu-hermes",
            "--rasa-url",
            shlex.quote(str(url)),
        ]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, intent_command, "intent")

        language = profile.get("intent.rasa.language")
        if language:
            intent_command.extend(["--rasa-language", shlex.quote(str(language))])

        config_yaml = profile.get("intent.rasa.config_yaml")
        if config_yaml:
            intent_command.extend(
                ["--rasa-config", shlex.quote(str(write_path(profile, config_yaml)))]
            )

        project_name = profile.get("intent.rasa.project_name")
        if project_name:
            intent_command.extend(["--rasa-project", shlex.quote(str(project_name))])

        examples = profile.get("intent.rasa.examples_markdown")
        if examples:
            intent_command.extend(
                ["--examples-path", shlex.quote(str(write_path(profile, examples)))]
            )

        replace_numbers = profile.get("intent.replace_numbers", True)
        if replace_numbers:
            intent_command.append("--replace-numbers")

            locale = profile.get("locale")
            if locale:
                intent_command.extend(["--number-language", str(locale)])

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        return intent_command

    if intent_system == "command":
        user_program = profile.get("intent.command.program")
        if not user_program:
            _LOGGER.error("intent.command.program is required")
            return []

        user_command = [user_program] + command_args(
            profile.get("intent.command.arguments", [])
        )

        intent_command = [
            "rhasspy-remote-http-hermes",
            "--nlu-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, intent_command, "intent")

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        add_ssl_args(intent_command, profile)

        # Training
        intent_train_system = profile.get("training.intent.system", "auto")
        if intent_train_system == "auto":
            train_program = profile.get("training.intent.command.program")
            if train_program:
                train_command = [train_program] + command_args(
                    profile.get("training.intent.command.arguments", [])
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

    if intent_system == "snips":
        language = profile.get("intent.snips.language") or profile.get("language", "en")
        if not language:
            _LOGGER.error("intent.snips.language is required")
            return []

        intent_command = [
            "rhasspy-snips-nlu-hermes",
            "--language",
            shlex.quote(str(language)),
        ]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        engine_path = profile.get("intent.snips.engine_dir")
        if engine_path:
            intent_command.extend(
                ["--engine-path", shlex.quote(str(write_path(profile, engine_path)))]
            )

        dataset_path = profile.get("intent.snips.dataset_file")
        if dataset_path:
            intent_command.extend(
                ["--dataset-path", shlex.quote(str(write_path(profile, dataset_path)))]
            )

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        return intent_command

    if intent_system == "remote":
        url = profile.get("intent.remote.url")
        if not url:
            _LOGGER.error("intent.remote.url is required")
            return []

        intent_command = ["rhasspy-remote-http-hermes", "--nlu-url", shlex.quote(url)]

        add_standard_args(
            profile,
            intent_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add --lang
        add_lang_args(profile, intent_command, "intent")

        # Case transformation
        if dictionary_casing:
            intent_command.extend(["--casing", dictionary_casing])

        add_ssl_args(intent_command, profile)

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
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for intent recognition system"""
    intent_command = get_intent_recognition(
        intent_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if intent_command:
        print("[program:intent_recognition]", file=out_file)
        print("command=", " ".join(intent_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def get_intent_handling(
    handle_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Get command for intent handling system"""
    if handle_system == "hass":
        url = profile.get("home_assistant.url")
        if not url:
            _LOGGER.error("home_assistant.url is required")
            return []

        handle_command = ["rhasspy-homeassistant-hermes", "--url", shlex.quote(url)]

        add_standard_args(
            profile,
            handle_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

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
        if not url:
            _LOGGER.error("handle.remote.url is required")
            return []

        handle_command = [
            "rhasspy-remote-http-hermes",
            "--handle-url",
            shlex.quote(url),
        ]

        add_standard_args(
            profile,
            handle_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        add_ssl_args(handle_command, profile)

        return handle_command

    if handle_system == "command":
        user_program = profile.get("handle.command.program")
        if not user_program:
            _LOGGER.error("handle.command.program is required")
            return []

        user_program = os.path.expandvars(user_program)
        user_command = [user_program] + command_args(
            profile.get("handle.command.arguments", [])
        )

        handle_command = [
            "rhasspy-remote-http-hermes",
            "--handle-command",
            shlex.quote(" ".join(str(v) for v in user_command)),
        ]

        add_standard_args(
            profile,
            handle_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        add_ssl_args(handle_command, profile)

        return handle_command

    raise ValueError(f"Unsupported intent handling system (got {handle_system})")


def print_intent_handling(
    handle_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for intent handling system"""
    handle_command = get_intent_handling(
        handle_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if handle_command:
        print("[program:intent_handling]", file=out_file)
        print("command=", " ".join(handle_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def get_dialogue(
    dialogue_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    master_site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for dialogue management system"""
    if dialogue_system == "rhasspy":
        dialogue_command = ["rhasspy-dialogue-hermes"]

        add_standard_args(
            profile,
            dialogue_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Seconds before a session times out
        session_timeout = str(profile.get("dialogue.session_timeout", ""))
        if session_timeout:
            dialogue_command.extend(["--session-timeout", session_timeout])

        # Add sounds (skip if no audio output system and no satellites)
        satellite_site_ids = profile.get("dialogue.satellite_site_ids")
        sound_system = profile.get("sounds.system", "dummy")
        if satellite_site_ids or (sound_system != "dummy"):
            for sound_name in ["wake", "recorded", "error"]:
                sound_path = profile.get(f"sounds.{sound_name}")
                if sound_path:
                    sound_path = os.path.expandvars(sound_path)
                    dialogue_command.extend(
                        ["--sound", sound_name, shlex.quote(str(sound_path))]
                    )

        if sound_system == "dummy":
            # Disable dialogue sounds on the base station for extra speed
            for site_id in master_site_ids:
                dialogue_command.extend(["--no-sound", site_id])

        volume = str(profile.get("dialogue.volume", ""))
        if volume:
            # Volume scalar from 0-1
            dialogue_command.extend(["--volume", volume])

        group_separator = str(profile.get("dialogue.group_separator", ""))
        if group_separator:
            # String separating groups from names in site ids.
            # Used to avoid multiple wake ups from satellites that are co-located.
            dialogue_command.extend(["--group-separator", group_separator])

        # ASR confidence
        speech_system = profile.get("speech_to_text.system", "dummy")
        if speech_system != "dummy":
            min_asr_confidence = profile.get(
                f"speech_to_text.{speech_system}.min_confidence"
            )
            if min_asr_confidence is not None:
                dialogue_command.extend(
                    ["--min-asr-confidence", str(min_asr_confidence)]
                )

        # TTS timeout
        say_chars_per_second = profile.get("dialogue.say_chars_per_second")
        if say_chars_per_second is not None:
            dialogue_command.extend(
                ["--say-chars-per-second", str(say_chars_per_second)]
            )

        # Feedback sound extensions (suffixes, e.g. '.wav')
        sound_suffixes = profile.get("dialogue.sound_suffixes")
        if sound_suffixes is not None:
            for sound_suffix in sound_suffixes:
                dialogue_command.extend(["--sound-suffix", str(sound_suffix)])

        return dialogue_command

    raise ValueError(f"Unsupported dialogue system (got {dialogue_system})")


def print_dialogue(
    dialogue_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    master_site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for dialogue management system"""
    dialogue_command = get_dialogue(
        dialogue_system,
        profile,
        site_ids,
        master_site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if dialogue_command:
        print("[program:dialogue]", file=out_file)
        print("command=", " ".join(dialogue_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------

# TODO: Add support for Google, NanoTTS


def get_text_to_speech(
    tts_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Get command for text to speech system"""
    if tts_system == "espeak":
        espeak_command = ["espeak", "--stdout", "-v", "{lang}"]

        espeak_command.extend(profile.get("text_to_speech.espeak.arguments", []))

        voice = str(profile.get("text_to_speech.espeak.voice", "")).strip()
        if not voice:
            voice = profile.get("language").strip()

        if not voice:
            voice = "en-us"

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in espeak_command)),
            "--voices-command",
            shlex.quote("espeak --voices | tail -n +2 | awk '{ print $2,$4 }'"),
            "--language",
            shlex.quote(str(voice)),
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.espeak.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "flite":
        flite_command = ["flite", "-o", "/dev/stdout", "-voice", "{lang}"]
        flite_command.extend(profile.get("text_to_speech.flite.arguments", []))

        # Text will be final argument
        flite_command.append("-t")

        voice = str(profile.get("text_to_speech.flite.voice", "slt")).strip()

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in flite_command)),
            "--voices-command",
            shlex.quote("flite -lv | cut -d: -f 2- | tr ' ' '\\n'"),
            "--language",
            shlex.quote(voice),
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.flite.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "picotts":
        extra_tts_args = []

        if shutil.which("pico2wave"):
            picotts_command = ["pico2wave", "-l", "{lang}", "-w", "{file}"]
        else:
            # Use nanotts instead
            picotts_command = ["nanotts", "-v", "{lang}", "-o", "{file}"]
            extra_tts_args.append("--text-on-stdin")

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in picotts_command)),
            "--temporary-wav",
        ] + extra_tts_args

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.picotts.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        picotts_language = str(profile.get("text_to_speech.picotts.language", ""))
        if picotts_language:
            tts_command.extend(["--language", shlex.quote(str(picotts_language))])
        else:
            # Fall back to profile locale
            locale = str(profile.get("locale", "")).strip()

            if locale:
                locale = locale.replace("_", "-")
                tts_command.extend(["--language", shlex.quote(str(locale))])

        return tts_command

    if tts_system == "nanotts":
        nanotts_command = ["nanotts", "-v", "{lang}", "-o", "{file}"]
        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in nanotts_command)),
            "--temporary-wav",
            "--text-on-stdin",
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.nanotts.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        nanotts_language = str(profile.get("text_to_speech.nanotts.language", ""))
        if nanotts_language:
            tts_command.extend(["--language", shlex.quote(str(nanotts_language))])
        else:
            # Fall back to profile locale
            locale = str(profile.get("locale", "")).strip()

            if locale:
                locale = locale.replace("_", "-")
                tts_command.extend(["--language", shlex.quote(str(locale))])

        langdir = str(profile.get("text_to_speech.nanotts.langdir", ""))

        if langdir:
            tts_command.extend(["-l", shlex.quote(os.path.expandvars(str(locale)))])

        return tts_command

    if tts_system == "marytts":
        url = profile.get("text_to_speech.marytts.url", "").strip()
        if not url:
            _LOGGER.error("text_to_speech.marytts.url is required")
            return []

        effects = profile.get("text_to_speech.marytts.effects", {})
        effects = [
            ("--data-urlencode", shlex.quote("%s=%s" % pair))
            for pair in effects.items()
        ]
        effects = list(itertools.chain(*effects))  # flatten tuples into list

        # Oh the things curl can do
        marytts_command = [
            '{%% if "/" in lang: %%}{%% set lang, voice = lang.split("/", maxsplit=1) %%}{%% endif %%}',
            "curl",
            "-sS",
            "-X",
            "GET",
            "-G",
            "--output",
            "-",
            "--data-urlencode",
            "INPUT_TYPE=TEXT",
            "--data-urlencode",
            "OUTPUT_TYPE=AUDIO",
            "--data-urlencode",
            "AUDIO=WAVE",
            "--data-urlencode",
            "LOCALE={{ lang }}",
            "{%% if voice: %%}--data-urlencode{%% endif %%}",
            "{%% if voice: %%}VOICE={{ voice }}{%% endif %%}",
            "--data-urlencode",
            'INPUT_TEXT="$0"',
        ]
        marytts_command += effects
        marytts_command.append(shlex.quote(url))

        voice = profile.get("text_to_speech.marytts.voice", "").strip()
        if voice:
            marytts_command.extend(["--data-urlencode", shlex.quote(f"VOICE={voice}")])

        # Combine into bash call so we can pass input text as $0
        bash_command = [
            "bash",
            "-c",
            shlex.quote(" ".join(str(v) for v in marytts_command)),
        ]

        # localhost:59125/process -> localhost:59125
        server_base_url = url
        if server_base_url.endswith("/"):
            server_base_url = server_base_url[:-1]

        if server_base_url.endswith("/process"):
            server_base_url = server_base_url[:-8]

        voices_command = [
            "curl",
            "-sS",
            "-X",
            "GET",
            shlex.quote(server_base_url + "/voices"),
        ]

        locale = str(profile.get("text_to_speech.marytts.locale", "en-US")).strip()

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in bash_command)),
            "--voices-command",
            shlex.quote(" ".join(str(v) for v in voices_command)),
            "--language",
            shlex.quote(locale),
            "--use-jinja2",
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.marytts.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "wavenet":

        voice = str(
            profile.get("text_to_speech.wavenet.voice", "en-US-Wavenet-C")
        ).strip()
        sample_rate = str(profile.get("text_to_speech.wavenet.sample_rate", 22050))

        credentials_json = profile.get("text_to_speech.wavenet.credentials_json")
        if not credentials_json:
            _LOGGER.error("text_to_speech.wavenet.credentials_json required")
            return []

        cache_dir = profile.get("text_to_speech.wavenet.cache_dir")
        if not cache_dir:
            _LOGGER.error("text_to_speech.wavenet.cache_dir is required")
            return []

        tts_command = [
            "rhasspy-tts-wavenet-hermes",
            "--credentials-json",
            shlex.quote(str(write_path(profile, credentials_json))),
            "--cache-dir",
            shlex.quote(str(write_path(profile, cache_dir))),
            "--voice",
            shlex.quote(voice),
            "--sample-rate",
            shlex.quote(sample_rate),
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.wavenet.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "opentts":
        url = profile.get("text_to_speech.opentts.url", "").strip()
        if not url:
            _LOGGER.error("text_to_speech.opentts.url is required")
            return []

        voice = profile.get("text_to_speech.opentts.voice", "").strip()
        voice_args = []
        if voice:
            voice_args = ["--data-urlencode", f"voice={voice}"]

        # Oh the things curl can do
        opentts_command = (
            ["curl", "-sS", "-X", "GET", "-G", "--output", "-"]
            + voice_args
            + ["--data-urlencode", 'text="$0"', shlex.quote(urljoin(url, "api/tts"))]
        )

        # Combine into bash call so we can pass input text as $0
        bash_command = [
            "bash",
            "-c",
            shlex.quote(" ".join(str(v) for v in opentts_command)),
        ]

        voices_command = [
            "curl",
            "-sS",
            "-X",
            "GET",
            shlex.quote(urljoin(url, "api/voices")),
            "|",
            "jq",
            "--raw-output",
            shlex.quote('keys[] as $k | "\\($k) \\(.[$k] | .name)"'),
        ]

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in bash_command)),
            "--voices-command",
            shlex.quote(" ".join(str(v) for v in voices_command)),
        ]

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.opentts.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "larynx":
        voices = typing.cast(
            typing.Dict[str, typing.Dict[str, typing.Any]],
            profile.get("text_to_speech.larynx.voices", {}),
        )

        if not voices:
            _LOGGER.error("text_to_speech.larynx.voices is required")
            return []

        default_voice = str(profile.get("text_to_speech.larynx.default_voice", ""))
        if not default_voice:
            default_voice = next(iter(voices.keys()))
            _LOGGER.warning("No default voice set. Using %s", default_voice)

        cache_dir = profile.get("text_to_speech.larynx.cache_dir")
        if not cache_dir:
            _LOGGER.error("text_to_speech.larynx.cache_dir is required")
            return []

        tts_command = [
            "rhasspy-tts-larynx-hermes",
            "--default-voice",
            shlex.quote(str(default_voice)),
            "--cache-dir",
            shlex.quote(str(write_path(profile, cache_dir))),
            "--gruut-dir",
            shlex.quote(str(write_path(profile, "gruut"))),
        ]

        larynx_vocoder = str(
            profile.get("text_to_speech.larynx.vocoder", "vctk_medium")
        )
        hifi_gan_path = "tts/larynx/hifi_gan"
        default_vocoder_type, default_vocoder_path = {
            "universal_large": ("hifi_gan", f"{hifi_gan_path}/universal_large"),
            "vctk_medium": ("hifi_gan", f"{hifi_gan_path}/vctk_medium"),
            "vctk_small": ("hifi_gan", f"{hifi_gan_path}/vctk_small"),
        }[larynx_vocoder]

        for voice, voice_settings in voices.items():
            # Voice settings look like this:
            # {
            #   "language": "GRUUT LANGUAGE (en-us)",
            #   "tts_type": "LARYNX MODEL TYPE (glow_tts)",
            #   "tts_path": "${RHASSPY_PROFILE}/tts//larynx/<language>/<voice>/",
            #   "vocoder_type": "LARYNX MODEL TYPE (hifi_gan)",
            #   "vocoder_path": "${RHASSPY_PROFILE}/tts/larynx/<vocoder>/<model>/"
            # }
            voice_language = str(voice_settings["language"])
            voice_tts_type = str(voice_settings["tts_type"])
            voice_tts_path = str(voice_settings["tts_path"])
            voice_vocoder_type = str(
                voice_settings.get("vocoder_type", default_vocoder_type)
            )
            voice_vocoder_path = str(
                voice_settings.get("vocoder_path", default_vocoder_path)
            )

            tts_command.extend(
                [
                    "--voice",
                    shlex.quote(voice),
                    shlex.quote(voice_language),
                    shlex.quote(voice_tts_type),
                    shlex.quote(str(write_path(profile, voice_tts_path))),
                    shlex.quote(voice_vocoder_type),
                    shlex.quote(str(write_path(profile, voice_vocoder_path))),
                ]
            )

            # Optional settings
            tts_settings: typing.Dict[str, typing.Any] = voice_settings.get(
                "tts_settings", {}
            )
            vocoder_settings: typing.Dict[str, typing.Any] = voice_settings.get(
                "vocoder_settings", {}
            )

            for tts_key, tts_value in tts_settings.items():
                tts_command.extend(
                    [
                        "--tts-setting",
                        shlex.quote(voice),
                        shlex.quote(str(tts_key)),
                        shlex.quote(str(tts_value)),
                    ]
                )

            for vocoder_key, vocoder_value in vocoder_settings.items():
                tts_command.extend(
                    [
                        "--vocoder-setting",
                        shlex.quote(voice),
                        shlex.quote(str(vocoder_key)),
                        shlex.quote(str(vocoder_value)),
                    ]
                )

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.larynx.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return tts_command

    if tts_system == "command":
        say_program = profile.get("text_to_speech.command.say_program")
        if not say_program:
            _LOGGER.error("text_to_speech.command.say_program is required")
            return []

        say_command = [say_program] + command_args(
            profile.get("text_to_speech.command.say_arguments", [])
        )

        tts_command = [
            "rhasspy-tts-cli-hermes",
            "--tts-command",
            shlex.quote(" ".join(str(v) for v in say_command)),
        ]

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        # Add volume scalar (0-1)
        volume = str(profile.get("text_to_speech.command.volume", ""))
        if volume:
            tts_command.extend(["--volume", volume])

        voices_program = profile.get("text_to_speech.command.voices_program")
        if voices_program:
            voices_command = [voices_program] + command_args(
                profile.get("text_to_speech.command.voices_arguments", [])
            )
            tts_command.extend(
                [
                    "--voices-command",
                    shlex.quote(" ".join(str(v) for v in voices_command)),
                ]
            )

        language = profile.get("text_to_speech.command.language")
        if language:
            tts_command.extend(["--language", shlex.quote(str(language))])

        return tts_command

    if tts_system == "remote":
        url = profile.get("text_to_speech.remote.url")
        if not url:
            _LOGGER.error("text_to_speech.remote.url is required")
            return []

        tts_command = ["rhasspy-remote-http-hermes", "--tts-url", shlex.quote(url)]

        add_standard_args(
            profile,
            tts_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        add_ssl_args(tts_command, profile)

        return tts_command

    raise ValueError(f"Unsupported text to speech system (got {tts_system})")


def print_text_to_speech(
    tts_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for text to speech system"""
    tts_command = get_text_to_speech(
        tts_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if tts_command:
        print("[program:text_to_speech]", file=out_file)
        print("command=", " ".join(tts_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def get_speakers(
    sound_system: str,
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for audio output system"""
    if sound_system == "aplay":
        play_command = ["aplay", "-q", "-t", "wav"]
        list_command = ["aplay", "-L"]
        sound_device = profile.get("sounds.aplay.device", "").strip()
        if sound_device:
            play_command.extend(["-D", str(sound_device)])

        output_command = [
            "rhasspy-speakers-cli-hermes",
            "--play-command",
            shlex.quote(" ".join(play_command)),
            "--list-command",
            shlex.quote(" ".join(list_command)),
        ]

        volume = str(profile.get("sounds.aplay.volume", ""))
        if volume:
            output_command.extend(["--volume", volume])

        add_standard_args(
            profile,
            output_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return output_command

    if sound_system == "command":
        # Command to play WAV files
        play_program = profile.get("sounds.command.play_program")
        if not play_program:
            _LOGGER.error("sounds.command.play_program is required")
            return []

        play_command = [play_program] + command_args(
            profile.get("sounds.command.play_arguments", [])
        )

        output_command = [
            "rhasspy-speakers-cli-hermes",
            "--play-command",
            shlex.quote(" ".join(str(v) for v in play_command)),
        ]

        add_standard_args(
            profile,
            output_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

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

    if sound_system == "remote":
        # POST WAV data to URL
        url = profile.get("sounds.remote.url")
        if not url:
            _LOGGER.error("sounds.remote.url is required")
            return []

        play_command = [
            "curl",
            "-s",
            "-X",
            "POST",
            "-H",
            "Content-Type: audio/wav",
            "--data-binary",
            "@-",
            shlex.quote(str(url)),
        ]

        output_command = [
            "rhasspy-speakers-cli-hermes",
            "--play-command",
            shlex.quote(" ".join(str(v) for v in play_command)),
        ]

        add_standard_args(
            profile,
            output_command,
            site_ids,
            mqtt_host,
            mqtt_port,
            mqtt_username,
            mqtt_password,
        )

        return output_command

    raise ValueError(f"Unsupported sound output system (got {sound_system})")


def print_speakers(
    sound_system: str,
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for audio output system"""
    output_command = get_speakers(
        sound_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if output_command:
        print("[program:speakers]", file=out_file)
        print("command=", " ".join(output_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------


def get_webhooks(
    webhooks: typing.Dict[str, typing.Any],
    profile: Profile,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> typing.List[str]:
    """Get command for webhooks"""
    webhook_command = ["rhasspy-remote-http-hermes"]

    add_standard_args(
        profile,
        webhook_command,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    add_ssl_args(webhook_command, profile)

    # Parse MQTT topics and urls
    topics_urls: typing.List[typing.Tuple[str, str]] = []
    for key, values in webhooks.items():
        if key == "awake":
            # Intepret has hotword detected event for all wakeword ids
            if isinstance(values, str):
                # Allow string or list of strings
                values = [values]

            topics_urls.extend(("hermes/hotword/+/detected", url) for url in values)
        elif key == "mqtt":
            # values is a dictionary with topic -> urls
            for topic, urls in values.items():
                if isinstance(urls, str):
                    # Allow string or list of strings
                    urls = [urls]

                topics_urls.extend((topic, url) for url in urls)

    for topic, url in topics_urls:
        webhook_command.extend(["--webhook", shlex.quote(topic), shlex.quote(url)])

    return webhook_command


def print_webhooks(
    webhooks: typing.Dict[str, typing.Any],
    profile: Profile,
    out_file: typing.TextIO,
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for webhooks"""
    webhook_command = get_webhooks(
        webhooks, profile, site_ids, mqtt_host, mqtt_port, mqtt_username, mqtt_password
    )

    if webhook_command:
        print("[program:webhooks]", file=out_file)
        print("command=", " ".join(webhook_command), sep="", file=out_file)
        write_boilerplate(out_file)


# -----------------------------------------------------------------------------
# docker compose
# -----------------------------------------------------------------------------


def profile_to_docker(profile: Profile, out_file: typing.TextIO, local_mqtt_port=12183):
    """Transform Rhasspy profile to docker-compose.yml"""
    services: typing.Dict[str, typing.Any] = {}

    # MQTT
    master_site_ids = str(profile.get("mqtt.site_id", "default")).split(",")

    mqtt_host = str(profile.get("mqtt.host", "localhost"))
    mqtt_port = int(profile.get("mqtt.port", 1883))

    mqtt_username = str(profile.get("mqtt.username", "")).strip()
    mqtt_password = str(profile.get("mqtt.password", "")).strip()

    remote_mqtt = str(profile.get("mqtt.enabled", False)).lower() == "true"
    if not remote_mqtt:
        # Use internal broker (mosquitto) on custom port
        mqtt_host = "mqtt"
        mqtt_port = local_mqtt_port
        mqtt_username = ""
        mqtt_password = ""
        compose_mqtt(services, mqtt_port=local_mqtt_port)

    # -------------------------------------------------------------------------

    # Microphone
    mic_system = profile.get("microphone.system", "dummy")
    if mic_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("microphone.satellite_site_ids", "")
        ).split(",")
        compose_microphone(
            mic_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Microphone disabled (system=%s)", mic_system)

    # Speakers
    sound_system = profile.get("sounds.system", "dummy")
    if sound_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("sounds.satellite_site_ids", "")).split(
            ","
        )
        compose_speakers(
            sound_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Speakers disabled (system=%s)", sound_system)

    # Wake Word
    wake_system = profile.get("wake.system", "dummy")
    if wake_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("wake.satellite_site_ids", "")).split(",")
        compose_wake(
            wake_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Wake word disabled (system=%s)", wake_system)

    # Speech to Text
    stt_system = profile.get("speech_to_text.system", "dummy")
    if stt_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("speech_to_text.satellite_site_ids", "")
        ).split(",")
        compose_speech_to_text(
            stt_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Speech to text disabled (system=%s)", stt_system)

    # Intent Recognition
    intent_system = profile.get("intent.system", "dummy")
    if intent_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("intent.satellite_site_ids", "")).split(
            ","
        )
        compose_intent_recognition(
            intent_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Intent recognition disabled (system=%s)", intent_system)

    # Text to Speech
    tts_system = profile.get("text_to_speech.system", "dummy")
    if tts_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(
            profile.get("text_to_speech.satellite_site_ids", "")
        ).split(",")
        compose_text_to_speech(
            tts_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Text to speech disabled (system=%s)", tts_system)

    # Dialogue Management
    dialogue_system = profile.get("dialogue.system", "dummy")
    if dialogue_system not in {"dummy", "hermes"}:
        satellite_site_ids = str(profile.get("dialogue.satellite_site_ids", "")).split(
            ","
        )
        compose_dialogue(
            dialogue_system,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            master_site_ids=master_site_ids,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )
    else:
        _LOGGER.debug("Dialogue disabled (system=%s)", dialogue_system)

    # Webhooks
    webhooks = profile.get("webhooks", {})
    webhook_events = [k for k in webhooks.keys() if k != "satellite_site_ids"]
    if webhook_events:
        satellite_site_ids = str(profile.get("webhooks.satellite_site_ids", "")).split(
            ","
        )
        compose_webhooks(
            webhooks,
            profile,
            services,
            site_ids=(master_site_ids + satellite_site_ids),
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
        )

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


def compose_microphone(
    mic_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for microphone system"""
    mic_command = get_microphone(
        mic_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if mic_command:
        service_name = mic_command.pop(0)
        services["microphone"] = {
            "image": f"rhasspy/{service_name}",
            "command": " ".join(mic_command),
            "devices": ["/dev/snd"],
            "depends_on": ["mqtt"],
            "tty": True,
        }


# -----------------------------------------------------------------------------


def compose_wake(
    wake_system: str,
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for wake system"""
    wake_command = get_wake(
        wake_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if wake_command:
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
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for speech to text system"""
    stt_command = get_speech_to_text(
        stt_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if stt_command:
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
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for intent recognition system"""
    intent_command = get_intent_recognition(
        intent_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if intent_command:
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
    site_ids: typing.List[str],
    master_site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for dialogue management system"""
    dialogue_command = get_dialogue(
        dialogue_system,
        profile,
        site_ids,
        master_site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if dialogue_command:
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
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for text to speech system"""
    tts_command = get_text_to_speech(
        tts_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if tts_command:
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
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for audio output system"""
    output_command = get_speakers(
        sound_system,
        profile,
        site_ids,
        mqtt_host,
        mqtt_port,
        mqtt_username,
        mqtt_password,
    )

    if output_command:
        service_name = output_command.pop(0)
        services["speakers"] = {
            "image": f"rhasspy/{service_name}",
            "command": " ".join(output_command),
            "devices": ["/dev/snd"],
            "depends_on": ["mqtt"],
            "tty": True,
        }


# -----------------------------------------------------------------------------


def compose_webhooks(
    webhooks: typing.Dict[str, typing.Any],
    profile: Profile,
    services: typing.Dict[str, typing.Any],
    site_ids: typing.List[str],
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
):
    """Print command for webhooks"""
    webhook_command = get_webhooks(
        webhooks, profile, site_ids, mqtt_host, mqtt_port, mqtt_username, mqtt_password
    )

    if webhook_command:
        service_name = webhook_command.pop(0)
        services["webhooks"] = {
            "image": f"rhasspy/{service_name}",
            "command": " ".join(webhook_command),
            "depends_on": ["mqtt"],
            "tty": True,
        }


# -----------------------------------------------------------------------------


def add_ssl_args(command: typing.List[str], profile: Profile):
    """Add --certfile and --keyfile arguments."""
    certfile = profile.get("home_assistant.pem_file")
    keyfile = profile.get("home_assistant.key_file")

    if certfile:
        command.extend(["--certfile", shlex.quote(os.path.expandvars(str(certfile)))])

    if keyfile:
        command.extend(["--keyfile", shlex.quote(os.path.expandvars(str(keyfile)))])


def add_silence_args(command: typing.List[str], profile: Profile):
    """Add silence detection arguments."""
    skip_sec = str(profile.get("command.webrtcvad.skip_sec", ""))
    if skip_sec:
        command.extend(["--voice-skip-seconds", skip_sec])

    min_sec = str(profile.get("command.webrtcvad.min_sec", ""))
    if min_sec:
        command.extend(["--voice-min-seconds", min_sec])

    max_sec = str(profile.get("command.webrtcvad.max_sec", ""))
    if max_sec:
        command.extend(["--voice-max-seconds", max_sec])

    speech_sec = str(profile.get("command.webrtcvad.speech_sec", ""))
    if speech_sec:
        command.extend(["--voice-speech-seconds", speech_sec])

    silence_sec = str(profile.get("command.webrtcvad.silence_sec", ""))
    if silence_sec:
        command.extend(["--voice-silence-seconds", silence_sec])

    before_sec = str(profile.get("command.webrtcvad.before_sec", ""))
    if before_sec:
        command.extend(["--voice-before-seconds", before_sec])

    vad_mode = str(profile.get("command.webrtcvad.vad_mode", ""))
    if vad_mode:
        command.extend(["--voice-sensitivity", vad_mode])

    silence_method = str(profile.get("command.webrtcvad.silence_method", ""))
    if silence_method:
        command.extend(["--voice-silence-method", silence_method])

    current_energy_threshold = str(
        profile.get("command.webrtcvad.current_energy_threshold", "")
    )
    if current_energy_threshold:
        command.extend(["--voice-current-energy-threshold", current_energy_threshold])

    max_energy = str(profile.get("command.webrtcvad.max_energy", ""))
    if max_energy:
        command.extend(["--voice-max-energy", max_energy])

    max_current_energy_ratio_threshold = str(
        profile.get("command.webrtcvad.max_current_energy_ratio_threshold", "")
    )
    if max_current_energy_ratio_threshold:
        command.extend(
            [
                "--voice-max-current-energy-ratio-threshold",
                max_current_energy_ratio_threshold,
            ]
        )


def command_args(
    arguments: typing.Optional[typing.Union[str, typing.List[str]]]
) -> typing.List[str]:
    """Parse command arguments as string or list."""
    if arguments:
        if isinstance(arguments, str):
            return shlex.split(arguments)

        return arguments

    return []


# -----------------------------------------------------------------------------


def write_path(profile: Profile, *path_parts) -> Path:
    """Get user writable path in profile."""
    return profile.user_profiles_dir.joinpath(profile.name, *path_parts)
