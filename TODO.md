# Оглавление
- [Оглавление](#оглавление)
- [Секцию описания окон](#секцию-описания-окон)
  - [Пример в settings.yaml](#пример-в-settingsyaml)

# Секцию описания окон

- [ ] Окна конечные (instance)
- [ ] Окна шаблонные (template): для создания окна из сценариев, подобие класса
- [ ] navbar/multihead/generic используют окна из windows по name

## Пример в settings.yaml

```yaml
windows:                    
  - name: Home
    title: 'Обзор'
    ui: Home.ui
  - name: Preferences
    title: 'Настройки'
    ui: Preferences.ui
```