"""
Определение тарифных планов
"""

from database.models import TariffPlan


def get_tariff_plans():
    """Получение всех активных тарифных планов"""
    tariffs = TariffPlan.select().where(TariffPlan.is_active == True)
    return [
        {
            "id": tariff.id,
            "name": tariff.name,
            "description": tariff.description,
            "price": tariff.price,
            "currency": tariff.currency,
            "duration_days": tariff.duration_days,
            "max_devices": tariff.max_devices,
            "speed_limit": tariff.speed_limit,
            "features": tariff.features_list,
        }
        for tariff in tariffs
    ]


def get_tariff_by_id(tariff_id):
    """Получение тарифа по ID"""
    try:
        tariff = TariffPlan.get_by_id(tariff_id)
        if tariff and tariff.is_active:
            return {
                "id": tariff.id,
                "name": tariff.name,
                "description": tariff.description,
                "price": tariff.price,
                "currency": tariff.currency,
                "duration_days": tariff.duration_days,
                "max_devices": tariff.max_devices,
                "speed_limit": tariff.speed_limit,
                "features": tariff.features_list,
            }
    except Exception:
        return None


def create_tariff_plan(
    name, description, price, duration_days, max_devices, speed_limit="unlimited"
):
    """Создание нового тарифного плана"""
    tariff = TariffPlan.create(
        name=name,
        description=description,
        price=price,
        duration_days=duration_days,
        max_devices=max_devices,
        speed_limit=speed_limit,
    )
    return tariff


def update_tariff_plan(tariff_id, **kwargs):
    """Обновление тарифного плана"""
    from playhouse.shortcuts import update_model_from_dict

    tariff = TariffPlan.get_by_id(tariff_id)
    if tariff:
        update_model_from_dict(tariff, kwargs)
        tariff.save()
        return True
    return False


def delete_tariff_plan(tariff_id):
    """Удаление тарифного плана"""
    tariff = TariffPlan.get_by_id(tariff_id)
    if tariff:
        tariff.is_active = False
        tariff.save()
        return True
    return False


def get_recommended_tariff(user_profile=None):
    """
    Получение рекомендованного тарифа для пользователя
    :param user_profile: профиль пользователя (необязательно)
    :return: рекомендованный тариф
    """
    # По умолчанию возвращаем самый популярный тариф
    # В реальном приложении можно использовать алгоритмы машинного обучения
    # для персонализированных рекомендаций

    # Получаем тарифы, отсортированные по популярности (в данном случае просто по цене)
    tariffs = (
        TariffPlan.select()
        .where(TariffPlan.is_active == True)
        .order_by(TariffPlan.price.asc())
    )

    if tariffs.count() > 0:
        recommended_tariff = tariffs[0]  # Базовый тариф как рекомендуемый

        # Если у нас есть профиль пользователя, можем вернуть более подходящий тариф
        if user_profile:
            # Простая логика: если пользователь указал, что ему важна скорость - даем тариф с высокой скоростью
            if user_profile.get("needs_high_speed"):
                high_speed_tariffs = tariffs.where(
                    TariffPlan.speed_limit == "unlimited"
                )
                if high_speed_tariffs.count() > 0:
                    recommended_tariff = high_speed_tariffs[0]

        return {
            "id": recommended_tariff.id,
            "name": recommended_tariff.name,
            "description": recommended_tariff.description,
            "price": recommended_tariff.price,
            "currency": recommended_tariff.currency,
            "duration_days": recommended_tariff.duration_days,
            "max_devices": recommended_tariff.max_devices,
            "speed_limit": recommended_tariff.speed_limit,
            "features": recommended_tariff.features_list,
        }

    return None
