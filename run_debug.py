import os
os.environ['FLASK_DEBUG'] = '1'

from app import app
app.debug = True
app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)