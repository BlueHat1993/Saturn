from agents.saturn_graph import graph_rag_app
import inspect

print('type:', type(graph_rag_app))
print('repr:', repr(graph_rag_app))
print('dir (public):', [d for d in dir(graph_rag_app) if not d.startswith('_')])
for name in ['run','invoke','execute','call','__call__']:
    print(name, 'present?', hasattr(graph_rag_app, name))
try:
    sig = inspect.signature(graph_rag_app)
    print('signature:', sig)
except Exception as e:
    print('signature error:', e)

# Try calling with a minimal state to see behavior (catch exceptions)
try:
    print('\nAttempting call with dict state...')
    out = graph_rag_app({'user_query': 'test'})
    print('call returned:', out)
except Exception as e:
    import traceback
    traceback.print_exc()
    print('call error:', e)

try:
    print('\nAttempting run method if present...')
    if hasattr(graph_rag_app, 'run'):
        out = getattr(graph_rag_app, 'run')({'user_query': 'test'})
        print('run returned:', out)
    else:
        print('no run method')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('run error:', e)
