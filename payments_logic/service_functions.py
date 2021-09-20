from django.contrib.auth.models import User


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def get_summary(data):
    new_data = []
    name_pairs = list()
    for row in data:

        deb_name = row['debitor__username']
        payer = row['source__payer__username']
        initial_value = row['total']
        pair = {deb_name, payer}

        for another_row in data:
            if another_row['debitor__username'] == deb_name and another_row['source__payer__username'] == payer:
                continue
            if another_row['debitor__username'] == payer and another_row['source__payer__username'] == deb_name:
                if pair in name_pairs:
                    break
                name_pairs.append(pair)
                if another_row['total'] > initial_value:
                    new_row = {'debitor': User.objects.get(username=another_row['debitor__username']),
                               'payer': User.objects.get(username=another_row['source__payer__username']),
                               'total': another_row['total'] - initial_value}
                elif another_row['total'] < initial_value:
                    new_row = {'debitor': User.objects.get(username=deb_name),
                               'payer': User.objects.get(username=payer),
                               'total': initial_value - another_row['total']}
                else:
                    continue
                new_data.append(new_row)
                break

        if pair not in name_pairs:
            name_pairs.append(pair)

            new_data.append({'debitor': User.objects.get(username=row['debitor__username']),
                             'payer': User.objects.get(username=row['source__payer__username']),
                             'total': initial_value})

    new_data = list(filter(lambda elem: elem['total'] > 0, new_data))
    return new_data
