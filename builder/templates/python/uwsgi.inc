[program:uwsgi]
command=uwsgi -s {{ supervisor_dir }}/uwsgi.sock --chmod-socket=660 --master --processes {{ config.uwsgi_processes|default("2") }} --home {{ virtualenv_dir }} --pythonpath {{ exec_dir }} --logdate {{ "--memory-report" if config.uwsgi_memory_report else "--disable-logging" }} {{ "--buffer-size " ~ config.uwsgi_buffer_size if config.uwsgi_buffer_size }} {{ "--harakiri " ~ config.uwsgi_harakiri if config.uwsgi_harakiri }} {{ "--enable-threads" if config.uwsgi_enable_threads }} {{ "--single-interpreter" if config.uwsgi_single_interpreter }}
directory={{ exec_dir }}
stdout_logfile={{ supervisor_dir }}/uwsgi.log
stderr_logfile={{ supervisor_dir }}/uwsgi_error.log
stopsignal=INT

{# vim: set ft=jinja: #}
