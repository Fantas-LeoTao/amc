# -*- coding: utf-8 -*-

import re

from flask import request

from flask.ext.wtf import Form
from wtforms.validators import DataRequired, Optional, Length, Email
from wtforms import StringField, FloatField, IntegerField, TextAreaField
from wtforms.fields.html5 import EmailField
from wtforms import ValidationError

from amc.models import AuthModel, UserModel


class UserInfoForm(Form):
    """后台创建用户，修改用户信息"""

    name = StringField(
        u'用户名',
        validators=[DataRequired(), Length(min=2, max=20)])
    phone = StringField(u'电话', validators=[Optional()])
    address = StringField(u'地址',
                          validators=[Optional(), Length(min=2, max=256)])
    account = EmailField(u'邮箱（即登录名）', validators=[DataRequired(), Email()])

    def validate_account(form, field):
        if 'id' in request.view_args:
            # 更新操作，排除自己账户
            id = request.view_args.get('id')
            user = UserModel.query.get(id)
            if (user and user.auth and
                    user.auth.account == field.data):
                return
        auth = AuthModel.get_by_account(field.data)
        if auth:
            raise ValidationError('Account exists')

    def validate_phone(form, field):
        re_mobile = re.compile(r'^((\+86)|(86))?(1)[3|4|5|7|8|]\d{9}$')
        if not re.match(re_mobile, field.data):
            raise ValidationError('Not a phone number')


class ProductInfoForm(Form):
    """后台创建产品，修改产品信息"""

    name = StringField(
        u'产品名称',
        validators=[DataRequired(), Length(min=2, max=20)])
    category = StringField(u'类别', validators=[DataRequired()], default='M')  # choose from GMS
    description = TextAreaField(u'描述', validators=[Optional()])
    price = FloatField(u'价格', validators=[DataRequired()])
    quantity = IntegerField(u'库存量', validators=[DataRequired()])
    safe_quantity = IntegerField(u'安全库存量', validators=[Optional()])
    made_in = StringField(u'产地',
                          validators=[DataRequired(),
                                      Length(min=2, max=20)])


class PurchaseInfoForm(Form):
    """后台创建采购事项，修改采购信息"""

    product_id = IntegerField(u'产品编号')
    product_quantity = IntegerField(u'采购数量')
    status = StringField(u'采购状态')  # choose from STATUS_BEGIN,STATUS_OVER


class PayInfoForm(Form):
    """后台创建账款事项，修改账款信息"""

    order_id = IntegerField(u'订单编号')
    status = StringField(u'账款状态')  # choose from STATUS_PENDING,STATUS_RECEIVED
