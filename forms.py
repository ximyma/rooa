from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FileField, IntegerField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    class Meta:
        csrf = False

class DocumentWritingForm(FlaskForm):
    template = SelectField('模板', choices=[('通知', '通知'), ('报告', '报告'), ('请示', '请示')])
    keywords = StringField('关键词', validators=[DataRequired()])

class PolishForm(FlaskForm):
    content = TextAreaField('待润色内容')

class ProofreadForm(FlaskForm):
    file = FileField('上传文件')
    scheme = SelectField('校对方案', choices=[('standard', '标准'), ('sensitive', '敏感信息')])

class SuggestionForm(FlaskForm):
    file = FileField('上传文件')
    department_duty = StringField('部门职责', validators=[DataRequired()])
    word_limit = IntegerField('字数限制')

class MeetingMinutesForm(FlaskForm):
    audio = FileField('录音文件')
    template = SelectField('会议模板', choices=[('通用', '通用'), ('专题', '专题')])