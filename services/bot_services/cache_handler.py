import hashlib
import json
import os
 
class CacheHandler:
    def __init__(self, cache_file_path="Services/cache_store.json"):
        self.cache_file_path = cache_file_path
        # Ensure the cache file exists
        if not os.path.exists(os.path.dirname(cache_file_path)):
            os.makedirs(os.path.dirname(cache_file_path))
        if not os.path.exists(cache_file_path):
            with open(cache_file_path, 'w') as f:
                json.dump({}, f)
 
    def generate_hash_key(self, jd_text, resume_text):
        combined = jd_text.strip() + resume_text.strip()
        return hashlib.md5(combined.encode()).hexdigest()
 
    def load_cache(self):
        if os.path.exists(self.cache_file_path):
            with open(self.cache_file_path, 'r') as f:
                return json.load(f)
        return {}
 
    def save_cache(self, cache):
        with open(self.cache_file_path, 'w') as f:
            json.dump(cache, f, indent=4)
 
    def get_cached_result(self, jd_text, resume_text):
        key = self.generate_hash_key(jd_text, resume_text)
        cache = self.load_cache()
        return cache.get(key)
 
    def store_result(self, jd_text, resume_text, result):
        key = self.generate_hash_key(jd_text, resume_text)
        cache = self.load_cache()
        cache[key] = result
        self.save_cache(cache)
 