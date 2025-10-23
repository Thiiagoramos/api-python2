# Importando as bibliotecas
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from geoalchemy2 import Geometry, Geography
import os

# Criando a instância do Flask
app = Flask(__name__)

# Configurando a conexão com o banco de dados PostgreSQL
# Substitua as informações de acordo com a sua configuração
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://app_user:senhaappentec@163.176.179.159:5432/ia_plantas'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Criando a instância do SQLAlchemy
db = SQLAlchemy(app)

# ==============================================================================
#                      Definição dos Modelos (Tabelas)
# ==============================================================================

## Tabela: public.users
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False) # Ajustado o tamanho
    email = db.Column(db.String(150), unique=True, nullable=False) # Ajustado o tamanho
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos (Opcional para GETs simples, mas bom para a estrutura)
    samples = db.relationship('Sample', backref='user', lazy=True)
    devices = db.relationship('Device', backref='user', lazy=True)
    annotations = db.relationship('Annotation', backref='annotator', lazy=True, foreign_keys='Annotation.annotator_id')

    def to_json(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

## Tabela: public.plants
class Plant(db.Model):
    __tablename__ = 'plants'

    id = db.Column(db.Integer, primary_key=True)
    nome_comum = db.Column(db.String(100), nullable=False)
    nome_cientifico = db.Column(db.String(150))
    descricao = db.Column(db.Text) # 'text' no BD mapeia para Text no SQLAlchemy

    # Relacionamentos
    samples = db.relationship('Sample', backref='plant', lazy=True)

    def to_json(self):
        return {
            'id': self.id,
            'nome_comum': self.nome_comum,
            'nome_cientifico': self.nome_cientifico,
            'descricao': self.descricao,
        }

## Tabela: public.devices
class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    users_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tipo = db.Column(db.String(50))
    modelo = db.Column(db.String(100))
    last_seen = db.Column(db.DateTime)
    # A coluna 'location' é do tipo geography(Point, 4326)
    location = db.Column(Geography('POINT', srid=4326)) 

    # Relacionamentos
    samples = db.relationship('Sample', backref='device', lazy=True)

    def to_json(self):
        # A representação de Geometry é mais complexa, vou retornar como string WKT
        location_wkt = self.location.wkt if self.location else None
        return {
            'id': self.id,
            'users_id': self.users_id,
            'tipo': self.tipo,
            'modelo': self.modelo,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'location': location_wkt
        }

## Tabela: public.samples
class Sample(db.Model):
    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'))
    image_path = db.Column(db.Text, nullable=False)
    thumb_path = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(Geography('POINT', srid=4326))
    weather_meta = db.Column(db.JSON) # Tipo 'jsonb' no BD
    notes = db.Column(db.Text)

    # Relacionamentos
    annotations = db.relationship('Annotation', backref='sample', lazy=True)
    diagnoses = db.relationship('Diagnose', backref='sample', lazy=True)

    def to_json(self):
        location_wkt = self.location.wkt if self.location else None
        return {
            'id': self.id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'plant_id': self.plant_id,
            'image_path': self.image_path,
            'thumb_path': self.thumb_path,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'location': location_wkt,
            'weather_meta': self.weather_meta,
            'notes': self.notes
        }

## Tabela: public.annotations
class Annotation(db.Model):
    __tablename__ = 'annotations'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'))
    annotator_id = db.Column(db.Integer, db.ForeignKey('users.id')) # Referencia user_id
    bbox = db.Column(db.JSON) # Tipo 'jsonb' no BD
    label = db.Column(db.String(100))
    confidence = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'annotator_id': self.annotator_id,
            'bbox': self.bbox,
            'label': self.label,
            'confidence': float(self.confidence) if self.confidence else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

## Tabela: public.diagnoses
class Diagnose(db.Model):
    __tablename__ = 'diagnoses'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'))
    model_version = db.Column(db.String(50))
    predicted_label = db.Column(db.String(100))
    confidence = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'model_version': self.model_version,
            'predicted_label': self.predicted_label,
            'confidence': float(self.confidence) if self.confidence else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

## Tabela: public.treatments
class Treatment(db.Model):
    __tablename__ = 'treatments'

    id = db.Column(db.Integer, primary_key=True)
    disease_label = db.Column(db.String(100))
    recomendacoes_texto = db.Column(db.Text)
    severity_level = db.Column(db.String(50))

    def to_json(self):
        return {
            'id': self.id,
            'disease_label': self.disease_label,
            'recomendacoes_texto': self.recomendacoes_texto,
            'severity_level': self.severity_level
        }

## Tabela: public.audit_logs
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            'id': self.id,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'action': self.action,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

## Tabela: public.spatial_ref_sys (Geralmente usada pelo PostGIS, mas incluída)
class SpatialRefSys(db.Model):
    __tablename__ = 'spatial_ref_sys'

    srid = db.Column(db.Integer, primary_key=True)
    auth_name = db.Column(db.String(256))
    auth_srid = db.Column(db.Integer)
    srtext = db.Column(db.String(2048))
    proj4text = db.Column(db.String(2048))

    def to_json(self):
        return {
            'srid': self.srid,
            'auth_name': self.auth_name,
            'auth_srid': self.auth_srid,
            'srtext': self.srtext,
            'proj4text': self.proj4text,
        }

##Tabela: public.sensores
class Sensores(db.Model):
    __tablename__ = 'sensores'

    id = db.Column(db.Integer, primary_key = True)
    umidade = db.Column(db.Numeric(5, 2))
    temperatura = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_json(self):
        return {
            'id': self.id,
            'umidade': float(self.umidade) if self.umidade else None,
            'temperatura': float(self.temperatura) if self.temperatura else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ==============================================================================
#                             Rotas GET
# ==============================================================================

### Usuários (users)
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.order_by(User.id.desc()).first()
    if users is None:
        return jsonify({}), 204
    else:
        return jsonify(users.to_json())

@app.route('/users/<int:id>', methods=['GET'])
def get_user_by_id(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


### Plantas (plants)
@app.route('/plants', methods=['GET'])
def get_plants():
    plants = Plant.query.order_by(Plant.id.desc()).first()
    if plants is None:
        return jsonify({}), 204
    else:
        return jsonify(plants.to_json())

@app.route('/plants/<int:id>', methods=['GET'])
def get_plant_by_id(id):
    plant = Plant.query.get_or_404(id)
    return jsonify(plant.to_json())


### Amostras (samples)
@app.route('/samples', methods=['GET'])
def get_samples():
    samples = Sample.query.order_by(Sample.id.desc()).first()
    if samples is None:
        return jsonify({}), 204
    else:
        return jsonify(samples.to_json())

@app.route('/samples/<int:id>', methods=['GET'])
def get_sample_by_id(id):
    sample = Sample.query.get_or_404(id)
    return jsonify(sample.to_json())


### Dispositivos (devices)
@app.route('/devices', methods=['GET'])
def get_devices():
    devices = Device.query.order_by(Device.id.desc()).first()
    if devices is None:
        return jsonify({}), 204
    else:
        return jsonify(devices.to_json())

@app.route('/devices/<int:id>', methods=['GET'])
def get_device_by_id(id):
    device = Device.query.get_or_404(id)
    return jsonify(device.to_json())


### Anotações (annotations)
@app.route('/annotations', methods=['GET'])
def get_annotations():
    annotations = Annotation.query.order_by(Annotation.id.desc()).first()
    if annotations is None:
        return jsonify({}), 204
    else:
        return jsonify(annotations.to_json())

@app.route('/annotations/<int:id>', methods=['GET'])
def get_annotation_by_id(id):
    annotation = Annotation.query.get_or_404(id)
    return jsonify(annotation.to_json())


### Diagnósticos (diagnoses)
@app.route('/diagnoses', methods=['GET'])
def get_diagnoses():
    diagnoses = Diagnose.query.order_by(Diagnose.id.desc()).first()
    if diagnoses is None:
        return jsonify({}), 204
    else:
        return jsonify(diagnoses.to_json())

@app.route('/diagnoses/<int:id>', methods=['GET'])
def get_diagnose_by_id(id):
    diagnose = Diagnose.query.get_or_404(id)
    return jsonify(diagnose.to_json())


### Tratamentos (treatments)
@app.route('/treatments', methods=['GET'])
def get_treatments():
    treatments = Treatment.query.order_by(Treatment.id.desc()).first()
    if treatments is None:
         return jsonify({}), 204
    else:
         return jsonify(treatments.to_json())
    # treatments = Treatment.query.all()
    # if not treatments:  # Verifica se a lista está vazia (treatments == [] ou treatments is None)
    #     return jsonify({}), 204
    # else:
    #     # Mapeia cada objeto na lista para a sua representação JSON
    #     return jsonify([t.to_json() for t in treatments])

@app.route('/treatments/<int:id>', methods=['GET'])
def get_treatment_by_id(id):
    treatment = Treatment.query.get_or_404(id)
    return jsonify(treatment.to_json())


### Logs de Auditoria (audit_logs)
@app.route('/audit_logs', methods=['GET'])
def get_audit_logs():
    audit_logs = AuditLog.query.order_by(AuditLog.id.desc()).first()
    if audit_logs is None:
        return jsonify({}), 204
    else:
        return jsonify(audit_logs.to_json())

@app.route('/audit_logs/<int:id>', methods=['GET'])
def get_audit_log_by_id(id):
    audit_log = AuditLog.query.get_or_404(id)
    return jsonify(audit_log.to_json())


### Sistema de Referência Espacial (spatial_ref_sys)
@app.route('/spatial_ref_sys', methods=['GET'])
def get_spatial_ref_sys():
    refs = SpatialRefSys.query.order_by(SpatialRefSys.id.desc()).first()
    if refs is None:
        return jsonify({}), 204
    else:
        return jsonify(refs.to_json())

@app.route('/spatial_ref_sys/<int:srid>', methods=['GET'])
def get_spatial_ref_sys_by_srid(srid):
    ref = SpatialRefSys.query.get_or_404(srid)
    return jsonify(ref.to_json())


##Sensores
@app.route('/sensores',  methods=['GET'])
def get_sensores():
    sensor = Sensores.query.order_by(Sensores.id.desc()).first()
    if sensor is None:
        return jsonify({}), 204
    else:
        return jsonify(sensor.to_json())
    
@app.route('/sensores/<int:srid>', methods=['GET'])
def get_sensores_by_id(srid):
    sensor = Sensores.query.get_or_404(srid)
    return jsonify(sensor.to_json())

@app.route('/sensores', methods=['POST'])
def add_sensor_data():
    """
    Rota POST: Recebe dados via POST e os salva no banco.
    Corpo esperado (JSON): {"temperatura": 25.5, "umidade": 60.0}
    """
    data = request.get_json()

    # Verifica se os dados mínimos necessários estão presentes
    if not data or 'temperatura' not in data or 'umidade' not in data:
        return jsonify({'error': 'Dados inválidos. JSON com "temperatura" e "umidade" é necessário.'}), 400

    try:
        nova_leitura = Sensores(
            temperatura=float(data['temperatura']),
            umidade=float(data['umidade'])
        )
        db.session.add(nova_leitura)
        db.session.commit()

        return jsonify({
            'message': 'Dados do sensor salvos com sucesso!',
            'id': nova_leitura.id
        }), 201

    except (ValueError, TypeError):
        # Captura erro se os valores não puderem ser convertidos para números
        return jsonify({'error': 'Valores de temperatura e umidade devem ser números.'}), 400
    except Exception as e:
        # Captura erros gerais (como problemas de conexão com o banco)
        db.session.rollback()
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500

# # Rota para adicionar um novo usuário
# @app.route('/users', methods=['POST'])
# def add_user():
#     dados = request.get_json()
#     if not dados or 'nome' not in dados or 'email' not in dados or 'role' not in dados:
#         return jsonify({'message': 'Dados de usuário inválidos'}), 400

#     novo_user = User(
#         nome=dados['nome'],
#         email=dados['email'],
#         role=dados['role']
#     )
#     db.session.add(novo_user)
#     db.session.commit()

#     return jsonify(novo_user.to_json()), 201 # 201 = Created

# # Rota para atualizar um usuário existente
# @app.route('/users/<int:id>', methods=['PUT'])
# def update_user(id):
#     user = User.query.get_or_404(id)
#     dados = request.get_json()

#     if 'nome' in dados:
#         user.nome = dados['nome']
#     if 'email' in dados:
#         user.email = dados['email']
#     if 'role' in dados:
#         user.role = dados['role']
    
#     db.session.commit()
#     return jsonify(user.to_json())

# # Rota para deletar um usuário
# @app.route('/users/<int:id>', methods=['DELETE'])
# def delete_user(id):
#     user = User.query.get_or_404(id)
#     db.session.delete(user)
#     db.session.commit()
#     return jsonify({'message': 'Usuário deletado com sucesso'}), 200


# Executando a API
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)