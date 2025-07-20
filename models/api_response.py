"""API响应模型"""

"""API响应模型"""

from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel, Field

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一API响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    code: Optional[int] = Field(None, description="响应代码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")
    
    class Config:
        json_encoders = {
            # 可以添加自定义编码器
        }
        
    @classmethod
    def success_response(cls, message: str = "操作成功", data: Any = None, code: int = 200):
        """创建成功响应"""
        from datetime import datetime
        return cls(
            success=True,
            message=message,
            data=data,
            code=code,
            timestamp=datetime.now().isoformat()
        )
    
    @classmethod
    def error_response(cls, message: str = "操作失败", data: Any = None, code: int = 500):
        """创建错误响应"""
        from datetime import datetime
        return cls(
            success=False,
            message=message,
            data=data,
            code=code,
            timestamp=datetime.now().isoformat()
        )