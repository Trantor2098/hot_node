from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bpy.types import Operator

class Reporter:
    active_ops: 'Operator' = None
    is_active_ops_warning_thrown: bool = False
    is_active_ops_error_thrown: bool = False

    @classmethod
    def set_active_ops(cls, ops: 'Operator|None'):
        cls.active_ops = ops
        if ops is None:
            cls.is_active_ops_warning_thrown = False
            cls.is_active_ops_error_thrown = False

    @classmethod
    def get_active_ops(cls):
        return cls.active_ops
    
    @classmethod
    def report_finish(cls, success_msg: str = "", warning_msg: str = "", error_msg: str = ""):
        """Report a success message which can change with the warning/error situation."""
        if cls.active_ops is not None:
            if cls.is_active_ops_error_thrown:
                cls.active_ops.report({'INFO'}, error_msg)
                cls.is_active_ops_error_thrown = False
                return 2
            elif cls.is_active_ops_warning_thrown:
                cls.active_ops.report({'INFO'}, warning_msg)
                cls.is_active_ops_warning_thrown = False
                return 1
            cls.active_ops.report({'INFO'}, success_msg)
            return 0
    
    @classmethod
    def report_warning(cls, message: str):
        """Report an operation warning."""
        if cls.active_ops is not None:
            cls.is_active_ops_warning_thrown: bool = True
            cls.active_ops.report({'WARNING'}, message)
            
    @classmethod
    def report_error(cls, message: str):
        """Report an operation error."""
        if cls.active_ops is not None:
            cls.is_active_ops_error_thrown = True
            cls.active_ops.report({'ERROR'}, message)