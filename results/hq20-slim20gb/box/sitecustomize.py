import os, sys, json, time

OUT = os.environ.get("HQTRACE", "/home/jamie/hq20/trace.jsonl")
STATE = {"model": os.environ.get("HQMODEL", ""), "revision": "", "config": "",
         "dtype_enum": "", "dtype_name": "", "names": {}}


def rss_bytes():
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except Exception:
        return -1
    return -1


def resident_bytes():
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL).decode()
        me = os.getpid()
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) == me:
                return int(float(parts[1])) * 1024 * 1024
    except Exception:
        return -1
    return -1


def rec(phase, **kw):
    try:
        mem = {}
        try:
            import torch
            if torch.cuda.is_initialized():
                mem = {
                    "mem_allocated": int(torch.cuda.memory_allocated()),
                    "mem_reserved": int(torch.cuda.memory_reserved()),
                    "mem_max_allocated": int(torch.cuda.max_memory_allocated()),
                    "mem_get_info": [int(x) for x in torch.cuda.mem_get_info()],
                    "device": torch.cuda.get_device_name(0),
                }
        except Exception:
            pass
        e = {"phase": phase, "ts": time.time(), "pid": os.getpid(),
             "role": os.path.basename(sys.argv[0]) if sys.argv else "",
             "pypath_set": bool(os.environ.get("PYTHONPATH")),
             "cuda_ready": bool(mem), "rss_bytes": rss_bytes(),
             "resident_bytes": resident_bytes(),
             "model_path": STATE["model"], "revision": STATE["revision"],
             "config": STATE["config"], "dtype_enum": STATE["dtype_enum"],
             "dtype_name": STATE["dtype_name"],
             "alloc_conf": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "")}
        e.update(mem)
        e.update(kw)
        with open(OUT, "a") as f:
            f.write(json.dumps(e, default=str) + "\n")
    except Exception as exc:
        try:
            with open(OUT, "a") as f:
                f.write(json.dumps({"phase": "trace-rec-error", "ts": time.time(),
                                    "pid": os.getpid(), "error": repr(exc)}) + "\n")
        except Exception:
            pass


def note_model(model_config):
    try:
        STATE["model"] = getattr(model_config, "model", STATE["model"])
        STATE["revision"] = str(getattr(model_config, "revision", ""))
        STATE["config"] = str(getattr(getattr(model_config, "hf_config", None), "model_type", ""))
        dt = getattr(model_config, "dtype", None)
        if dt is not None:
            STATE["dtype_enum"] = str(getattr(dt, "value", ""))
            STATE["dtype_name"] = str(dt).replace("torch.", "")
    except Exception:
        pass


def draft_context():
    try:
        from vllm.model_executor.model_loader.default_loader import shared_mtp_target
        return shared_mtp_target.get() is not None
    except Exception:
        return False


def layer_name(layer):
    return STATE["names"].get(id(layer), type(layer).__name__)


def layer_dtypes(layer):
    out = {}
    try:
        for n, p in list(layer.named_parameters(recurse=False))[:8]:
            out[n] = str(p.dtype).replace("torch.", "")
    except Exception:
        pass
    return out


def install():
    import vllm.model_executor.model_loader.base_loader as bl
    import vllm.model_executor.model_loader.utils as lutils
    import vllm.v1.spec_decode.llm_base_proposer as lbp
    import vllm.v1.attention.backends.triton_attn as ta
    import vllm.v1.core.kv_cache_utils as kvu
    import vllm.v1.worker.gpu_model_runner as gr

    orig_pwals = lutils.process_weights_after_loading
    def pwals(model, model_config, target_device):
        try:
            STATE["names"] = {id(m): n for n, m in model.named_modules()}
        except Exception:
            pass
        return orig_pwals(model, model_config, target_device)
    lutils.process_weights_after_loading = pwals

    orig_load = bl.BaseModelLoader.load_model
    def load_model(self, vllm_config, model_config, *a, **kw):
        note_model(model_config)
        is_draft = draft_context()
        rec("p3_draft_before_construct" if is_draft else "p1_before_target_construction",
            fn="base_loader.load_model", **({"draft": True} if is_draft else {}))
        out = orig_load(self, vllm_config, model_config, *a, **kw)
        rec("p4x_draft_after_post_load" if is_draft else "p2_after_target_weights_and_repacks",
            fn="base_loader.load_model", **({"draft": True} if is_draft else {}))
        return out
    bl.BaseModelLoader.load_model = load_model

    try:
        import vllm.model_executor.model_loader.default_loader as dl
        if "load_model" in vars(dl.DefaultModelLoader):
            orig_dl = dl.DefaultModelLoader.load_model
            def load_model_d(self, vllm_config, model_config, *a, **kw):
                note_model(model_config)
                is_draft = draft_context()
                rec("p3_draft_before_construct" if is_draft else "p1_before_target_construction",
                    fn="default_loader.load_model", **({"draft": True} if is_draft else {}))
                out = orig_dl(self, vllm_config, model_config, *a, **kw)
                rec("p4x_draft_after_post_load" if is_draft else "p2_after_target_weights_and_repacks",
                    fn="default_loader.load_model", **({"draft": True} if is_draft else {}))
                return out
            dl.DefaultModelLoader.load_model = load_model_d
    except Exception:
        pass

    try:
        from vllm.model_executor.kernels.linear.mixed_precision.MPLinearKernel import MPLinearKernel
        orig_tp = MPLinearKernel._transform_param
        def transform_param(self, layer, name, fn, *a, **kw):
            out = orig_tp(self, layer, name, fn, *a, **kw)
            rec("p4_after_marlin_repack", module=layer_name(layer), param=name,
                kernel=type(self).__name__, dtypes=layer_dtypes(layer))
            return out
        MPLinearKernel._transform_param = transform_param
    except Exception as exc:
        rec("trace-hook-error", hook="MPLinearKernel._transform_param", error=repr(exc))

    orig_pload = lbp.SpecDecodeBaseProposer.load_model
    def proposer_load(self, target_model, *a, **kw):
        rec("p3_before_draft_model_construct", fn="SpecDecodeBaseProposer.load_model")
        out = orig_pload(self, target_model, *a, **kw)
        try:
            lm = target_model.get_language_model() if hasattr(target_model, "get_language_model") else target_model
            t_inner = getattr(lm, "model", None)
            t_embed = getattr(t_inner, "embed_tokens", None)
            d_inner = getattr(self.model, "model", None)
            d_embed = getattr(d_inner, "embed_tokens", None)
            rec("p5_after_embedding_head_sharing",
                fn="SpecDecodeBaseProposer.load_model",
                embed_identity=d_embed is t_embed and t_embed is not None,
                head_identity=getattr(self.model, "lm_head", None) is getattr(lm, "lm_head", None),
                shared_modules=len(getattr(self.model, "_mtp_shared_modules", ()) or ()),
                draft_only=bool(getattr(self.model, "_mtp_draft_only", False)))
        except Exception as exc:
            rec("p5_after_embedding_head_sharing", identity_check_error=repr(exc))
        return out
    lbp.SpecDecodeBaseProposer.load_model = proposer_load

    try:
        orig_acq = ta.mq3d_scratch_acquire
        def scratch_acquire(plan, *a, **kw):
            out = orig_acq(plan, *a, **kw)
            fields = {}
            for k in ("num_heads_q", "num_heads_kv", "headdim", "headdim_padded",
                      "capacity", "max_num_batched_tokens", "max_num_seqs",
                      "seq_threshold_3D", "max_query_len_3d", "row_bytes"):
                if hasattr(plan, k):
                    fields[k] = getattr(plan, k)
            bufs = {}
            try:
                import torch
                for k, v in vars(plan).items():
                    if isinstance(v, torch.Tensor):
                        bufs[k] = {"shape": list(v.shape), "dtype": str(v.dtype).replace("torch.", "")}
                for k, v in (getattr(out, "__dict__", {}) or {}).items():
                    if isinstance(v, torch.Tensor):
                        bufs[k] = {"shape": list(v.shape), "dtype": str(v.dtype).replace("torch.", "")}
            except Exception:
                pass
            rec("p6a_after_int4_scratch_alloc", plan=fields, buffers=bufs, fn="mq3d_scratch_acquire")
            return out
        ta.mq3d_scratch_acquire = scratch_acquire
    except Exception as exc:
        rec("trace-hook-error", hook="mq3d_scratch_acquire", error=repr(exc))

    try:
        orig_cap = kvu.update_kv_cache_capacity
        def update_cap(vllm_config, kv_cache_config, *a, **kw):
            out = orig_cap(vllm_config, kv_cache_config, *a, **kw)
            rec("p6b_after_kv_alloc",
                kv_cache_size_tokens=getattr(vllm_config.cache_config, "kv_cache_size_tokens", None),
                kv_max_concurrency=getattr(vllm_config.cache_config, "kv_cache_max_concurrency", None),
                max_model_len=getattr(vllm_config.model_config, "max_model_len", None),
                fn="update_kv_cache_capacity")
            return out
        kvu.update_kv_cache_capacity = update_cap
    except Exception as exc:
        rec("trace-hook-error", hook="update_kv_cache_capacity", error=repr(exc))

    for cls_name in ("GPUModelRunner", "V1ModelRunner"):
        cls = getattr(gr, cls_name, None)
        if cls is None:
            continue
        for meth in ("_allocate_kv_cache_tensors", "initialize_kv_cache"):
            orig = getattr(cls, meth, None)
            if orig is None or not callable(orig):
                continue
            def mk(orig=orig, meth=meth, cls_name=cls_name):
                def wrapped(self, *a, **kw):
                    out = orig(self, *a, **kw)
                    rec("p6b_after_kv_alloc", fn=cls_name + "." + meth)
                    return out
                return wrapped
            setattr(cls, meth, mk())
        orig_cg = getattr(cls, "_capture_cudagraphs", None)
        if orig_cg is not None and callable(orig_cg):
            def wrapped_cg(self, *a, **kw):
                out = orig_cg(self, *a, **kw)
                rec("p6c_after_cuda_graph_capture", fn=cls_name + "._capture_cudagraphs")
                return out
            cls._capture_cudagraphs = wrapped_cg
    rec("trace-installed", python=sys.version.split()[0])


try:
    install()
except Exception as exc:
    rec("trace-install-error", error=repr(exc))
