# -*- coding: utf-8 -*-
import secrets
import os
import json
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

LOG_DIR = '/app/data/logs'
os.makedirs(LOG_DIR, exist_ok=True)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


class FeedView(LoginRequiredMixin, TemplateView):
    template_name = "social/feed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Social Feed"
        return context


@csrf_exempt
def register_simple(request):
    """
    Simple registration - just username, no password needed.
    Password is auto-generated and shown once.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        if not username:
            return JsonResponse({'error': '用户名不能为空'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': '用户名已存在'}, status=400)

        # Generate random password
        password = secrets.token_urlsafe(8)

        # Create user
        user = User.objects.create_user(username=username, password=password)

        return JsonResponse({
            'success': True,
            'username': username,
            'password': password,
            'message': f'用户 {username} 创建成功！密码是: {password}（请告诉用户）'
        })

    return JsonResponse({'error': '仅支持 POST'}, status=405)


@csrf_exempt
def client_log(request):
    """
    Accept log messages from client and save to file.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            level = data.get('level', 'info')
            message = data.get('message', '')
            context = data.get('context', {})
            user = request.user.username if request.user.is_authenticated else 'anonymous'
            ip = get_client_ip(request)

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            log_file = os.path.join(LOG_DIR, f'client_{datetime.now().strftime("%Y%m%d")}.log')

            log_entry = {
                'timestamp': timestamp,
                'level': level,
                'user': user,
                'ip': ip,
                'message': message,
                'context': context
            }

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'POST only'}, status=405)