# -*- coding: utf-8 -*-

from flask import (Blueprint, views, render_template,
                   redirect, url_for, abort)

from flask.ext.login import current_user, login_required

from amc.models import (OrderModel, OrderProductModel,
                        OrderHistoryModel, PayModel, LackedProductHistoryModel)
from amc.utils import now

bp = Blueprint('order', __name__)


class TrolleyView(views.MethodView):

    template = 'front/shopping_trolley.html'

    @login_required
    def get(self):
        trolley = current_user.trolley
        total = 0
        products = trolley.products
        for item in products:
            total += item.product.price * item.product_quantity
        return render_template(self.template, products=products, total=total)


class TrolleyCommitView(views.MethodView):
    """点击提交，生成订单后清空购物车
       本来可以和TrolleyView放一起使用post方法来提交，
       考虑到没有表单提交，所以分开用get请求提交订单"""

    @login_required
    def get(self):
        items = current_user.trolley.products
        if not items:
            abort(404, u'购物车为空')

        flag = False
        # 判断有没有库存不够
        for item in items:
            if item.lacked_quantity != 0:
                # 某件产品库存不足，添加缺件记录
                flag = True
                LackedProductHistoryModel.create(
                    product_id=item.product_id,
                    user_id=current_user.id,
                    quantity=item.lacked_quantity)

        if flag:
            abort(409, u'产品库存不足')

        # 创建订单，载入历史
        order = OrderModel.create(user_id=current_user.id)
        OrderHistoryModel.create(
            order_id=order.id,
            status=order.status,
            operator_id=current_user.id)

        # 填充订单信息，将购物车结账清算
        for item in items:
            product = item.product
            OrderProductModel.create(
                order_id=order.id,
                product_id=item.product_id,
                product_quantity=item.product_quantity,
                product_price=product.price)

            # 修改库存
            product.quantity -= item.product_quantity
            product.date_updated = now()
            product.save()

            # 修改库存低于安全库存自动新增采购
            # 但是采购成本不固定，需要管理员新建采购单
            if not product.is_safe:
                pass

            # 清空购物车
            item.delete()

        return redirect(url_for('user.order'))


class OrderCancelView(views.MethodView):
    """用户取消订单"""

    STATUS_ALLOW = [OrderModel.STATUS_LAUNCH, OrderModel.STATUS_CONFIRM]

    @login_required
    def get(self, id):
        order = OrderModel.query.get(id)
        if not order:
            abort(404, u'订单不存在')
        if order.user_id != current_user.id:
            # 非当前用户的订单
            abort(403, u'非当前用户订单')
        if order.status not in self.STATUS_ALLOW:
            # 订单处于不被允许取消的状态
            abort(403, u'订单不允许取消')

        # 修改库存
        for item in order.products:
            product = item.product
            product.quantity += item.product_quantity
            product.date_updated = now()
            product.save()
            # 这里不能delete，否则取消掉的订单为空订单
            # item.delete()

        # 更新状态，载入历史
        order.update(
            status=OrderModel.STATUS_CANCEL,
            date_updated=now())
        OrderHistoryModel.create(
            order_id=id,
            status=order.status,
            operator_id=current_user.id)

        return redirect(url_for('user.order'))


class OrderSuccessView(views.MethodView):
    """用户确认收获，生成收款单"""

    @login_required
    def get(self, id):
        order = OrderModel.query.get(id)
        if not order:
            abort(404, u'订单不存在')
        if order.user_id != current_user.id:
            # 非当前用户的订单
            abort(403, u'非当前用户订单')
        if order.status != OrderModel.STATUS_DISPATCH:
            # 订单处不处于货物发出状态
            abort(403, u'订单未发货')

        # 更新状态，载入历史
        order.update(
            status=OrderModel.STATUS_SUCCESS,
            date_updated=now())
        OrderHistoryModel.create(
            order_id=id,
            status=order.status,
            operator_id=current_user.id)

        # 生成收款单
        PayModel.create(
            order_id=id,
            amount=order.order_price)

        return redirect(url_for('user.order'))


class OrderReturnView(views.MethodView):
    """申请退货"""

    @login_required
    def get(self, id):
        order = OrderModel.query.get(id)
        if not order:
            abort(404, u'订单不存在')
        if order.user_id != current_user.id:
            # 非当前用户的订单
            abort(403, u'非当前用户订单')
        if order.status != OrderModel.STATUS_DISPATCH:
            # 订单处不处于货物发出状态
            abort(403, u'订单未发货')

        # 更新状态，载入历史
        order.update(
            status=OrderModel.STATUS_RETURN,
            date_updated=now())
        OrderHistoryModel.create(
            order_id=id,
            status=order.status,
            operator_id=current_user.id)

        return redirect(url_for('user.order'))


bp.add_url_rule(
    '/trolley/',
    view_func=TrolleyView.as_view('trolley'))
bp.add_url_rule(
    '/trolley/commit/',
    view_func=TrolleyCommitView.as_view('trolley_commit'))
bp.add_url_rule(
    '/order/cancel/<int:id>/',
    view_func=OrderCancelView.as_view('order_cancel'))
bp.add_url_rule(
    '/order/success/<int:id>/',
    view_func=OrderSuccessView.as_view('order_success'))
bp.add_url_rule(
    '/order/return/<int:id>/',
    view_func=OrderReturnView.as_view('order_return'))
