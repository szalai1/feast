import importlib
import struct
from typing import Any

import mmh3

from feast import errors
from feast.infra.online_stores.online_store import OnlineStore
from feast.protos.feast.storage.Redis_pb2 import RedisKeyV2 as RedisKeyProto
from feast.protos.feast.types.EntityKey_pb2 import EntityKey as EntityKeyProto


def get_online_store_from_config(online_store_config: Any,) -> OnlineStore:
    """Get the offline store from offline store config"""

    module_name = online_store_config.__module__
    qualified_name = type(online_store_config).__name__
    store_class_name = qualified_name.replace("Config", "")
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        # The original exception can be anything - either module not found,
        # or any other kind of error happening during the module import time.
        # So we should include the original error as well in the stack trace.
        raise errors.FeastModuleImportError(
            module_name, module_type="OnlineStore"
        ) from e

    # Try getting the provider class definition
    try:
        online_store_class = getattr(module, store_class_name)
    except AttributeError:
        # This can only be one type of error, when class_name attribute does not exist in the module
        # So we don't have to include the original exception here
        raise errors.FeastClassImportError(
            module_name, store_class_name, class_type="OnlineStore"
        ) from None
    return online_store_class()


def _redis_key(project: str, entity_key: EntityKeyProto):
    redis_key = RedisKeyProto(
        project=project,
        entity_names=entity_key.join_keys,
        entity_values=entity_key.entity_values,
    )
    return redis_key.SerializeToString()


def _mmh3(key: str):
    """
    Calculate murmur3_32 hash which is equal to scala version which is using little endian:
        https://stackoverflow.com/questions/29932956/murmur3-hash-different-result-between-python-and-java-implementation
        https://stackoverflow.com/questions/13141787/convert-decimal-int-to-little-endian-string-x-x
    """
    key_hash = mmh3.hash(key, signed=False)
    return bytes.fromhex(struct.pack("<Q", key_hash).hex()[:8])
