# -*- coding: utf-8 -*-
import datetime
import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy, slugify
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager as TaggitTaggableManager
from taggit.models import GenericTaggedItemBase, TagBase

from babybuddy.site_settings import NapSettings
from core.utils import random_color, timezone_aware_duration


def validate_date(date, field_name):
    """
    Confirm that a date is not in the future.
    :param date: a timezone aware date instance.
    :param field_name: the name of the field being checked.
    :return:
    """
    if date and date > timezone.localdate():
        raise ValidationError(
            {field_name: _("Date can not be in the future.")}, code="date_invalid"
        )


def validate_duration(model, max_duration=datetime.timedelta(hours=24)):
    """
    Basic sanity checks for models with a duration
    :param model: a model instance with 'start' and 'end' attributes
    :param max_duration: maximum allowed duration between start and end time
    :return:
    """
    if model.start and model.end:
        # Compare and calculate in UTC to account for DST changes between dates.
        start = model.start.astimezone(datetime.timezone.utc)
        end = model.end.astimezone(datetime.timezone.utc)
        if start > end:
            raise ValidationError(
                _("Start time must come before end time."), code="end_before_start"
            )
        if end - start > max_duration:
            raise ValidationError(_("Duration too long."), code="max_duration")


def _format_dt(dt):
    return formats.date_format(timezone.localtime(dt), "SHORT_DATETIME_FORMAT")


def validate_unique_period(queryset, model):
    """
    Confirm that model's start and end date do not intersect with other
    instances.
    :param queryset: a queryset of instances to check against.
    :param model: a model instance with 'start' and 'end' attributes
    :return:
    """
    if model.id:
        queryset = queryset.exclude(id=model.id)
    if model.start and model.end:
        conflicting = queryset.filter(start__lt=model.end, end__gt=model.start).first()
        if conflicting:
            url = reverse(
                f"core:{conflicting.model_name}-update",
                args=[conflicting.id],
            )
            link = (
                f'<a href="{url}">{conflicting} '
                f"({_format_dt(conflicting.start)} - "
                f"{_format_dt(conflicting.end)})</a>"
            )
            raise ValidationError(
                mark_safe(
                    f'{_("Another entry intersects the specified time period.")} '
                    f'{_("Conflicting entry")}: {link}'
                ),
                code="period_intersection",
            )


def validate_time(time, field_name):
    """
    Confirm that a time is not in the future.
    :param time: a timezone aware datetime instance.
    :param field_name: the name of the field being checked.
    :return:
    """
    if time and time > timezone.localtime():
        raise ValidationError(
            {field_name: _("Date/time can not be in the future.")}, code="time_invalid"
        )


class Tag(TagBase):
    model_name = "tag"
    DARK_COLOR = "#101010"
    LIGHT_COLOR = "#EFEFEF"

    color = models.CharField(
        verbose_name="颜色",
        max_length=32,
        default=random_color,
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$")],
    )
    last_used = models.DateTimeField(
        verbose_name="最后使用",
        default=timezone.now,
        blank=False,
    )

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = [Lower("name")]
        verbose_name = "标签"
        verbose_name_plural = "标签"

    @property
    def complementary_color(self):
        if not self.color:
            return self.DARK_COLOR

        r, g, b = [int(x, 16) for x in re.match("#(..)(..)(..)", self.color).groups()]
        yiq = ((r * 299) + (g * 587) + (b * 114)) // 1000
        if yiq >= 128:
            return self.DARK_COLOR
        else:
            return self.LIGHT_COLOR


class Tagged(GenericTaggedItemBase):
    tag = models.ForeignKey(
        Tag,
        verbose_name="标签",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )

    def save_base(self, *args, **kwargs):
        """
        Update last_used of the used tag, whenever it is used in a
        save-operation.
        """
        self.tag.last_used = timezone.now()
        self.tag.save()
        return super().save_base(*args, **kwargs)


class TaggableManager(TaggitTaggableManager):
    pass


class BMI(models.Model):
    model_name = "bmi"
    child = models.ForeignKey(
        "Child", on_delete=models.CASCADE, related_name="bmi", verbose_name="孩子"
    )
    bmi = models.FloatField(blank=False, null=False, verbose_name="BMI")
    date = models.DateField(
        blank=False, default=timezone.localdate, null=False, verbose_name="日期"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-date", "-id"]
        verbose_name = "BMI"
        verbose_name_plural = "BMI"

    def __str__(self):
        return "BMI"

    def clean(self):
        validate_date(self.date, "date")


class Child(models.Model):
    model_name = "child"
    first_name = models.CharField(max_length=255, verbose_name="名")
    last_name = models.CharField(
        blank=True, max_length=255, verbose_name="姓"
    )
    birth_date = models.DateField(blank=False, null=False, verbose_name="出生日期")
    birth_time = models.TimeField(blank=True, null=True, verbose_name="出生时间")
    slug = models.SlugField(
        allow_unicode=True,
        blank=False,
        editable=False,
        max_length=100,
        unique=True,
        verbose_name="Slug",
    )
    picture = models.ImageField(
        blank=True, null=True, upload_to="child/picture/", verbose_name="图片"
    )

    objects = models.Manager()

    cache_key_count = "core.child.count"

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["last_name", "first_name"]
        verbose_name = "孩子"
        verbose_name_plural = "孩子们"

    def __str__(self):
        return self.name()

    def save(self, *args, **kwargs):
        self.slug = slugify(self, allow_unicode=True)
        super(Child, self).save(*args, **kwargs)
        cache.set(self.cache_key_count, Child.objects.count(), None)

    def delete(self, using=None, keep_parents=False):
        super(Child, self).delete(using, keep_parents)
        cache.set(self.cache_key_count, Child.objects.count(), None)

    def name(self, reverse=False):
        if not self.last_name:
            return self.first_name
        if reverse:
            return "{}, {}".format(self.last_name, self.first_name)
        return "{} {}".format(self.first_name, self.last_name)

    def birth_datetime(self):
        if self.birth_time:
            return timezone.make_aware(
                datetime.datetime.combine(self.birth_date, self.birth_time)
            )
        return self.birth_date

    @classmethod
    def count(cls):
        """Get a (cached) count of total number of Child instances."""
        return cache.get_or_set(cls.cache_key_count, Child.objects.count, None)


class DiaperChange(models.Model):
    model_name = "diaperchange"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="diaper_change",
        verbose_name="孩子",
    )
    time = models.DateTimeField(
        blank=False, default=timezone.localtime, null=False, verbose_name="时间"
    )
    wet = models.BooleanField(verbose_name="湿")
    solid = models.BooleanField(verbose_name="固体")
    color = models.CharField(
        blank=True,
        choices=[
            ("black", "黑色"),
            ("brown", "棕色"),
            ("green", "绿色"),
            ("yellow", "黄色"),
        ],
        max_length=255,
        verbose_name="颜色",
    )
    amount = models.FloatField(blank=True, null=True, verbose_name="用量")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-time"]
        verbose_name = "尿布更换"
        verbose_name_plural = "尿布更换"

    def __str__(self):
        return "尿布更换"

    def attributes(self):
        attributes = []
        if self.wet:
            attributes.append(self._meta.get_field("wet").verbose_name)
        if self.solid:
            attributes.append(self._meta.get_field("solid").verbose_name)
        if self.color:
            attributes.append(self.get_color_display())
        return attributes

    def clean(self):
        validate_time(self.time, "time")


class Feeding(models.Model):
    model_name = "feeding"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="feeding",
        verbose_name="孩子",
    )
    start = models.DateTimeField(
        blank=False,
        default=timezone.localtime,
        null=False,
        verbose_name="开始时间",
    )
    end = models.DateTimeField(
        blank=False, default=timezone.localtime, null=False, verbose_name="结束时间"
    )
    duration = models.DurationField(
        editable=False, null=True, verbose_name="持续时间"
    )
    type = models.CharField(
        choices=[
            ("breast milk", "母乳"),
            ("formula", "配方奶"),
            ("fortified breast milk", "强化母乳"),
            ("solid food", "辅食"),
        ],
        max_length=255,
        verbose_name="类型",
    )
    method = models.CharField(
        choices=[
            ("bottle", "奶瓶"),
            ("left breast", "左侧"),
            ("right breast", "右侧"),
            ("both breasts", "双侧"),
            ("parent fed", "家长喂"),
            ("self fed", "自己吃"),
        ],
        max_length=255,
        verbose_name="方式",
    )
    amount = models.FloatField(blank=True, null=True, verbose_name="用量")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-start"]
        verbose_name = "喂养"
        verbose_name_plural = "喂养"

    def __str__(self):
        return "喂养"

    def save(self, *args, **kwargs):
        if self.start and self.end:
            self.duration = timezone_aware_duration(self.start, self.end)
        super(Feeding, self).save(*args, **kwargs)

    def clean(self):
        validate_time(self.start, "start")
        validate_duration(self)
        validate_unique_period(Feeding.objects.filter(child=self.child), self)


class HeadCircumference(models.Model):
    model_name = "head_circumference"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="head_circumference",
        verbose_name="孩子",
    )
    head_circumference = models.FloatField(
        blank=False, null=False, verbose_name="头围"
    )
    date = models.DateField(
        blank=False, default=timezone.localdate, null=False, verbose_name="日期"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-date", "-id"]
        verbose_name = "头围"
        verbose_name_plural = "头围"

    def __str__(self):
        return "头围"

    def clean(self):
        validate_date(self.date, "date")


class Height(models.Model):
    model_name = "height"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="height",
        verbose_name="孩子",
    )
    height = models.FloatField(blank=False, null=False, verbose_name="身高")
    date = models.DateField(
        blank=False, default=timezone.localdate, null=False, verbose_name="日期"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-date", "-id"]
        verbose_name = "身高"
        verbose_name_plural = "身高"

    def __str__(self):
        return "身高"

    def clean(self):
        validate_date(self.date, "date")


class HeightPercentile(models.Model):
    model_name = "height percentile"
    age_in_days = models.DurationField(null=False)
    p3_height = models.FloatField(null=False)
    p15_height = models.FloatField(null=False)
    p50_height = models.FloatField(null=False)
    p85_height = models.FloatField(null=False)
    p97_height = models.FloatField(null=False)
    sex = models.CharField(
        null=False,
        max_length=255,
        choices=[
            ("girl", "女孩"),
            ("boy", "男孩"),
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["age_in_days", "sex"], name="unique_age_sex_height"
            )
        ]


class Note(models.Model):
    model_name = "note"
    child = models.ForeignKey(
        "Child", on_delete=models.CASCADE, related_name="note", verbose_name="孩子"
    )
    note = models.TextField(verbose_name="备注")
    time = models.DateTimeField(
        blank=False, default=timezone.localtime, verbose_name="时间"
    )
    image = models.ImageField(
        blank=True, null=True, upload_to="notes/images/", verbose_name="图片"
    )
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-time"]
        verbose_name = "备注"
        verbose_name_plural = "备注"

    def __str__(self):
        return "备注"


class Pumping(models.Model):
    model_name = "pumping"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="pumping",
        verbose_name="孩子",
    )
    start = models.DateTimeField(
        blank=False,
        default=timezone.localtime,
        null=False,
        verbose_name="开始时间",
    )
    end = models.DateTimeField(
        blank=False,
        default=timezone.localtime,
        null=False,
        verbose_name="结束时间",
    )
    duration = models.DurationField(
        editable=False,
        null=True,
        verbose_name="持续时间",
    )
    amount = models.FloatField(blank=False, null=False, verbose_name="用量")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-start"]
        verbose_name = "吸奶"
        verbose_name_plural = "吸奶"

    def __str__(self):
        return "吸奶"

    def save(self, *args, **kwargs):
        if self.start and self.end:
            self.duration = timezone_aware_duration(self.start, self.end)
        super(Pumping, self).save(*args, **kwargs)

    def clean(self):
        validate_time(self.start, "start")
        validate_duration(self)
        validate_unique_period(Pumping.objects.filter(child=self.child), self)


class Sleep(models.Model):
    model_name = "sleep"
    child = models.ForeignKey(
        "Child", on_delete=models.CASCADE, related_name="sleep", verbose_name="孩子"
    )
    start = models.DateTimeField(
        blank=False,
        default=timezone.localtime,
        null=False,
        verbose_name="开始时间",
    )
    end = models.DateTimeField(
        blank=False, default=timezone.localtime, null=False, verbose_name="结束时间"
    )
    nap = models.BooleanField(null=False, blank=True, verbose_name="小睡")
    duration = models.DurationField(
        editable=False, null=True, verbose_name="持续时间"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()
    settings = NapSettings(_("Nap settings"))

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-start"]
        verbose_name = "睡眠"
        verbose_name_plural = "睡眠"

    def __str__(self):
        return "睡眠"

    def save(self, *args, **kwargs):
        if self.nap is None:
            self.nap = (
                Sleep.settings.nap_start_min
                <= timezone.localtime(self.start).time()
                <= Sleep.settings.nap_start_max
            )
        if self.start and self.end:
            self.duration = timezone_aware_duration(self.start, self.end)
        super(Sleep, self).save(*args, **kwargs)

    def clean(self):
        validate_time(self.start, "start")
        validate_time(self.end, "end")
        validate_duration(self)
        validate_unique_period(Sleep.objects.filter(child=self.child), self)


class Temperature(models.Model):
    model_name = "temperature"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="temperature",
        verbose_name="孩子",
    )
    temperature = models.FloatField(
        blank=False, null=False, verbose_name="体温"
    )
    time = models.DateTimeField(
        blank=False, default=timezone.localtime, null=False, verbose_name="时间"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-time"]
        verbose_name = "体温"
        verbose_name_plural = "体温"

    def __str__(self):
        return "体温"

    def clean(self):
        validate_time(self.time, "time")


class Timer(models.Model):
    model_name = "timer"
    child = models.ForeignKey(
        "Child",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="timers",
        verbose_name="孩子",
    )
    name = models.CharField(
        blank=True, max_length=255, null=True, verbose_name="名称"
    )
    start = models.DateTimeField(
        default=timezone.now, blank=False, verbose_name="开始时间"
    )
    active = models.BooleanField(default=True, editable=False, verbose_name="活跃")
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="timers",
        verbose_name="用户",
    )

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-start"]
        verbose_name = "计时器"
        verbose_name_plural = "计时器"

    def __str__(self):
        return self.name or f"计时器 #{self.id}"

    @property
    def title_with_child(self):
        """Get Timer title with child name in parenthesis."""
        title = str(self)
        # Only actually add the name if there is more than one Child instance.
        if title and self.child and Child.count() > 1:
            title = format_lazy("{title} ({child})", title=title, child=self.child)
        return title

    @property
    def user_username(self):
        """Get Timer user's name with a preference for the full name."""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.get_username()

    def duration(self):
        return timezone.now() - self.start

    def restart(self):
        """Restart the timer."""
        self.start = timezone.now()
        self.save()

    def stop(self):
        """Stop (delete) the timer."""
        self.delete()

    def save(self, *args, **kwargs):
        self.name = self.name or None
        super(Timer, self).save(*args, **kwargs)

    def clean(self):
        validate_time(self.start, "start")


class TummyTime(models.Model):
    model_name = "tummytime"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="tummy_time",
        verbose_name="孩子",
    )
    start = models.DateTimeField(
        blank=False,
        default=timezone.localtime,
        null=False,
        verbose_name="开始时间",
    )
    end = models.DateTimeField(
        blank=False, default=timezone.localtime, null=False, verbose_name="结束时间"
    )
    duration = models.DurationField(
        editable=False, null=True, verbose_name="持续时间"
    )
    milestone = models.CharField(
        blank=True, max_length=255, verbose_name="里程碑"
    )
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-start"]
        verbose_name = "俯卧时间"
        verbose_name_plural = "俯卧时间"

    def __str__(self):
        return "趴趴时间"

    def save(self, *args, **kwargs):
        if self.start and self.end:
            self.duration = timezone_aware_duration(self.start, self.end)
        super(TummyTime, self).save(*args, **kwargs)

    def clean(self):
        validate_time(self.start, "start")
        validate_time(self.end, "end")
        validate_duration(self)
        validate_unique_period(TummyTime.objects.filter(child=self.child), self)


class Weight(models.Model):
    model_name = "weight"
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="weight",
        verbose_name="孩子",
    )
    weight = models.FloatField(blank=False, null=False, verbose_name="体重")
    date = models.DateField(
        blank=False, default=timezone.localdate, null=False, verbose_name="日期"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    tags = TaggableManager(blank=True, through=Tagged)

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-date", "-id"]
        verbose_name = "体重"
        verbose_name_plural = "体重"

    def __str__(self):
        return "体重"

    def clean(self):
        validate_date(self.date, "date")


class WeightPercentile(models.Model):
    model_name = "weight percentile"
    age_in_days = models.DurationField(null=False)
    p3_weight = models.FloatField(null=False)
    p15_weight = models.FloatField(null=False)
    p50_weight = models.FloatField(null=False)
    p85_weight = models.FloatField(null=False)
    p97_weight = models.FloatField(null=False)
    sex = models.CharField(
        null=False,
        max_length=255,
        choices=[
            ("girl", "女孩"),
            ("boy", "男孩"),
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["age_in_days", "sex"], name="unique_age_sex"
            )
        ]

    def __str__(self):
        return f"Sex: {self.sex}, Age: {self.age_in_days} days, p3: {self.p3_weight} kg, p15: {self.p15_weight} kg, p50: {self.p50_weight} kg, p85: {self.p85_weight} kg, p97: {self.p97_weight} kg"
