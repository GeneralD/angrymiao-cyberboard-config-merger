"""User choice enumerations for type-safe UI interactions"""

from enum import Enum


class UserChoice(Enum):
    """Main user choices for workflow control"""
    PROCEED = "proceed"
    RESTART = "restart"
    BACK_TO_MAPPING = "back_to_mapping"
    CANCELLED = "cancelled"


class LEDAction(Enum):
    """LED configuration action choices"""
    KEEP_BASE = "keep_base"
    REPLACE = "replace"
    COMBINE = "combine"
    BACK = "back"


class NextAction(Enum):
    """Next action choices after LED configuration"""
    ADD_ANOTHER = "add_another"
    FINISH = "finish"
    BACK = "back"


class SaveMethod(Enum):
    """File save method choices"""
    NEW_FILE = "new_file"
    OVERWRITE = "overwrite"
    BACK = "back"


class ConfirmChoice(Enum):
    """Confirmation dialog choices"""
    YES = "yes"
    NO = "no"


class NoFilesAction(Enum):
    """Actions when no files are found"""
    RETRY = "retry"
    RELOAD_CONFIG = "reload_config"
    EXIT = "exit"