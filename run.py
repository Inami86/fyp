import os
from app import create_app

env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    is_dev = (env == 'development')
    # host=0.0.0.0 permette accesso da smartphone sulla stessa rete Wi-Fi
    app.run(debug=is_dev, host='0.0.0.0', port=5000)
