from django.views.generic import ListView, DetailView

from .models import Post


class PostList(ListView):
    model = Post
    template_name = 'post_list.html'
    context_object_name = 'posts'
    queryset = Post.objects.all().order_by('-dt_created')


class PostContent(DetailView):
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post_content'
