# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: tts_service.proto
# Protobuf Python Version: 6.31.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 6, 31, 0, "", "tts_service.proto"
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from .google.api import annotations_pb2 as google_dot_api_dot_annotations__pb2
from .yandex.cloud.ai.tts.v3 import \
    tts_pb2 as yandex_dot_cloud_dot_ai_dot_tts_dot_v3_dot_tts__pb2

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x11tts_service.proto\x12\x10speechkit.tts.v3\x1a yandex/cloud/ai/tts/v3/tts.proto\x1a\x1cgoogle/api/annotations.proto2\x96\x02\n\x0bSynthesizer\x12\x98\x01\n\x12UtteranceSynthesis\x12+.speechkit.tts.v3.UtteranceSynthesisRequest\x1a,.speechkit.tts.v3.UtteranceSynthesisResponse"%\x82\xd3\xe4\x93\x02\x1f"\x1a/tts/v3/utteranceSynthesis:\x01*0\x01\x12l\n\x0fStreamSynthesis\x12(.speechkit.tts.v3.StreamSynthesisRequest\x1a).speechkit.tts.v3.StreamSynthesisResponse"\x00(\x01\x30\x01\x42\\\n\x1ayandex.cloud.api.ai.tts.v3Z>github.com/yandex-cloud/go-genproto/yandex/cloud/ai/tts/v3;ttsb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "tts_service_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals["DESCRIPTOR"]._loaded_options = None
    _globals["DESCRIPTOR"]._serialized_options = (
        b"\n\032yandex.cloud.api.ai.tts.v3Z>github.com/yandex-cloud/go-genproto/yandex/cloud/ai/tts/v3;tts"
    )
    _globals["_SYNTHESIZER"].methods_by_name[
        "UtteranceSynthesis"
    ]._loaded_options = None
    _globals["_SYNTHESIZER"].methods_by_name[
        "UtteranceSynthesis"
    ]._serialized_options = (
        b'\202\323\344\223\002\037"\032/tts/v3/utteranceSynthesis:\001*'
    )
    _globals["_SYNTHESIZER"]._serialized_start = 104
    _globals["_SYNTHESIZER"]._serialized_end = 382
# @@protoc_insertion_point(module_scope)
