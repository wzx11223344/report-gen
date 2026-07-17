"""
数据源适配器模块

提供多种数据源接入方式，支持 CSV / JSON / SQLite / Python 字典
等数据源的统一读取接口。
"""

import csv
import json
import sqlite3
import io
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class DataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def read(self) -> List[Dict[str, Any]]:
        """读取数据并返回字典列表"""
        ...

    @abstractmethod
    def validate(self) -> bool:
        """验证数据源是否可用"""
        ...

    def get_column_names(self) -> List[str]:
        """获取列名"""
        data = self.read()
        if not data:
            return []
        return list(data[0].keys())

    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要信息"""
        data = self.read()
        if not data:
            return {"row_count": 0, "columns": []}

        summary = {
            "row_count": len(data),
            "columns": list(data[0].keys()),
            "column_types": {},
        }

        if data:
            first_row = data[0]
            for key in first_row:
                summary["column_types"][key] = type(first_row[key]).__name__

        return summary


class CSVDataSource(DataSource):
    """CSV 文件数据源"""

    def __init__(self, filepath: str, encoding: str = "utf-8", delimiter: str = ","):
        """
        初始化 CSV 数据源

        Args:
            filepath: CSV 文件路径
            encoding: 文件编码，默认 utf-8
            delimiter: 分隔符，默认逗号
        """
        self.filepath = filepath
        self.encoding = encoding
        self.delimiter = delimiter

    def read(self) -> List[Dict[str, Any]]:
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                data = []
                for row in reader:
                    # 尝试将数值字符串转换为数字
                    processed_row = {}
                    for key, value in row.items():
                        processed_row[key] = self._try_parse(value)
                    data.append(processed_row)
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"CSV 文件不存在: {self.filepath}")
        except Exception as e:
            raise RuntimeError(f"读取 CSV 文件失败: {e}")

    def validate(self) -> bool:
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                # 检查是否有表头和数据
                headers = reader.fieldnames
                if not headers:
                    return False
                # 尝试读取第一行
                next(reader, None)
                return True
        except Exception:
            return False

    @staticmethod
    def _try_parse(value: str) -> Any:
        """尝试将字符串转换为数值类型"""
        if value is None or value.strip() == "":
            return None
        stripped = value.strip()
        # 尝试转 int
        try:
            return int(stripped)
        except ValueError:
            pass
        # 尝试转 float
        try:
            return float(stripped)
        except ValueError:
            pass
        # 保留字符串
        return stripped


class JSONDataSource(DataSource):
    """JSON 文件数据源"""

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        """
        初始化 JSON 数据源

        Args:
            filepath: JSON 文件路径
            encoding: 文件编码
        """
        self.filepath = filepath
        self.encoding = encoding

    def read(self) -> List[Dict[str, Any]]:
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 如果 JSON 根节点是字典，尝试找到第一个列表值
                for key, value in data.items():
                    if isinstance(value, list):
                        return value
                return [data]
            if isinstance(data, list):
                return data
            return [{"value": data}]
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON 文件不存在: {self.filepath}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 解析失败: {e}")
        except Exception as e:
            raise RuntimeError(f"读取 JSON 文件失败: {e}")

    def validate(self) -> bool:
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                json.load(f)
            return True
        except Exception:
            return False


class SQLiteDataSource(DataSource):
    """SQLite 数据库数据源"""

    def __init__(self, db_path: str, query: str, params: Optional[List[Any]] = None):
        """
        初始化 SQLite 数据源

        Args:
            db_path: 数据库文件路径
            query: SQL 查询语句
            params: 查询参数
        """
        self.db_path = db_path
        self.query = query
        self.params = params or []

    def read(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(self.query, self.params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"SQLite 查询失败: {e}")
        finally:
            if conn:
                conn.close()

    def validate(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False


class DictDataSource(DataSource):
    """Python 字典数据源（内存数据）"""

    def __init__(self, data: List[Dict[str, Any]]):
        """
        初始化字典数据源

        Args:
            data: 字典列表格式的数据
        """
        self._data = data

    def read(self) -> List[Dict[str, Any]]:
        return self._data

    def validate(self) -> bool:
        return isinstance(self._data, list) and all(
            isinstance(row, dict) for row in self._data
        )


def create_datasource(
    source: Union[str, List[Dict[str, Any]], Dict[str, Any]],
    **kwargs,
) -> DataSource:
    """
    工厂函数：根据输入自动创建合适的数据源

    Args:
        source: 数据源，可以是文件路径或字典列表
        **kwargs: 传递给数据源的额外参数

    Returns:
        对应的 DataSource 实例

    Raises:
        ValueError: 无法识别的数据源类型
    """
    if isinstance(source, str):
        if source.endswith(".csv"):
            return CSVDataSource(source, **kwargs)
        elif source.endswith(".json"):
            return JSONDataSource(source, **kwargs)
        elif source.endswith(".db") or source.endswith(".sqlite"):
            query = kwargs.pop("query", "SELECT * FROM data")
            return SQLiteDataSource(source, query, **kwargs)
        else:
            raise ValueError(f"无法从文件后缀识别数据源类型: {source}")
    elif isinstance(source, list) and all(isinstance(row, dict) for row in source):
        return DictDataSource(source)
    elif isinstance(source, dict):
        return DictDataSource([source])
    else:
        raise ValueError(f"不支持的数据源类型: {type(source).__name__}")
