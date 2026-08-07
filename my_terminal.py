AttributeError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/tredge-quant-terminal/my_terminal.py", line 157, in <module>
    full_df, spot_price = fetch_precise_option_chain("NIFTY", live_expiry_list[0])
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 471, in __call__
    return self._get_or_create_cached_value(args, kwargs, spinner_message)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 527, in _get_or_create_cached_value
    return self._handle_cache_miss(cache, value_key, func_args, func_kwargs)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 589, in _handle_cache_miss
    computed_value = self._info.func(*func_args, **func_kwargs)
File "/mount/src/tredge-quant-terminal/my_terminal.py", line 128, in fetch_precise_option_chain
    ce_iv = round(np.uniform(12.0, 22.0) if abs(strike - spot) < 500 else np.uniform(18.0, 30.0), 2)
                                                                          ^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/numpy/__init__.py", line 769, in __getattr__
    raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")
