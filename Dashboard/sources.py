# -*- coding: utf-8 -*-
"""
数据源抽象：把「列举 CSV + 读取内容 + 变更指纹」统一成一个接口，
使聚合逻辑与存储位置（本地目录 / 阿里云 OSS）解耦。

每个 Source 提供：
  · signature()  -> 可哈希元组，用于缓存判断（文件集 + 大小 + 修改时间有变才重算）
  · iter_csv()   -> 逐个产出 (文件名, 排序键, 文本流)；排序键用于挑选「最新」会员快照
"""
import glob
import io
import os


class LocalSource:
    """读取本地目录下的 *.csv（开发 / 单机用）。"""

    def __init__(self, root):
        self.root = root

    def signature(self):
        sig = []
        if os.path.isdir(self.root):
            for n in sorted(os.listdir(self.root)):
                if n.lower().endswith(".csv"):
                    try:
                        st = os.stat(os.path.join(self.root, n))
                        sig.append((n, st.st_size, int(st.st_mtime)))
                    except OSError:
                        pass
        return tuple(sig)

    def iter_csv(self):
        for p in sorted(glob.glob(os.path.join(self.root, "*.csv"))):
            try:
                mtime = os.path.getmtime(p)
                fh = open(p, encoding="utf-8-sig", newline="")
            except OSError:
                continue
            yield os.path.basename(p), mtime, fh


class OssSource:
    """从阿里云 OSS bucket 的指定前缀下读取 *.csv（ECS + OSS 部署用）。

    依赖 oss2（pip install oss2）。鉴权优先级：
      1. ECS 实例 RAM 角色（环境变量 OSS_RAM_ROLE，最安全，无需在机器上放密钥）
      2. AccessKey（OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET）
    其余环境变量：OSS_ENDPOINT、OSS_BUCKET、OSS_PREFIX（默认 raw-data/）、
                 OSS_REGION（用 V4 签名时需要，如 cn-hongkong）。
    """

    def __init__(self, endpoint, bucket, prefix="raw-data/", region=None,
                 key_id=None, key_secret=None, ram_role=None):
        import oss2  # 延迟导入：本地无 oss2 也能跑 LocalSource
        self.oss2 = oss2
        self.prefix = prefix or ""
        if ram_role:
            from oss2.credentials import EcsRamRoleCredentialsProvider
            auth = oss2.ProviderAuthV4(EcsRamRoleCredentialsProvider(ram_role)) \
                if region else oss2.ProviderAuth(EcsRamRoleCredentialsProvider(ram_role))
        elif region:
            auth = oss2.AuthV4(key_id, key_secret)
        else:
            auth = oss2.Auth(key_id, key_secret)
        if region:
            self.bucket = oss2.Bucket(auth, endpoint, bucket, region=region)
        else:
            self.bucket = oss2.Bucket(auth, endpoint, bucket)

    def _objects(self):
        for obj in self.oss2.ObjectIterator(self.bucket, prefix=self.prefix):
            if obj.key.lower().endswith(".csv"):
                yield obj

    def signature(self):
        sig = []
        for obj in self._objects():
            # last_modified 为 epoch 秒（int），etag 兜底
            sig.append((obj.key, obj.size, int(obj.last_modified or 0), obj.etag or ""))
        sig.sort()
        return tuple(sig)

    def iter_csv(self):
        objs = sorted(self._objects(), key=lambda o: o.key)
        for obj in objs:
            data = self.bucket.get_object(obj.key).read()
            name = obj.key.split("/")[-1]
            yield name, int(obj.last_modified or 0), io.StringIO(data.decode("utf-8-sig"))


def from_env(local_root):
    """按环境变量决定数据源：设了 OSS_BUCKET 用 OSS，否则用本地目录。"""
    if os.environ.get("OSS_BUCKET"):
        return OssSource(
            endpoint=os.environ["OSS_ENDPOINT"],
            bucket=os.environ["OSS_BUCKET"],
            prefix=os.environ.get("OSS_PREFIX", "raw-data/"),
            region=os.environ.get("OSS_REGION") or None,
            key_id=os.environ.get("OSS_ACCESS_KEY_ID"),
            key_secret=os.environ.get("OSS_ACCESS_KEY_SECRET"),
            ram_role=os.environ.get("OSS_RAM_ROLE") or None,
        ), "OSS"
    return LocalSource(local_root), "本地目录"
