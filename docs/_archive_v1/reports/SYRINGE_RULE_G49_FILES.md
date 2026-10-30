# G49 — файлы и проверка путей

Все перечисленные пути абсолютные, проверяются внутри C:\Dev\Game. Исходники чужой параллельной работы не включены как изменения G49. BuyerCatalog содержит также сохранённую добавку G48.

Unity автоматически обновляет совместные Library/кеши импорта; это не ручные изменения ассетов/сцен. Ни один защищённый файл Claude скрипт не изменяет.

## Исходники, данные, отчёты

| Абсолютный путь | Причина |
|---|---|
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerCatalog.cs | G49: один интерфейс/lookup цен с разрешённым fallback; изменения G48 сохранены. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerRules.cs | Снят запрет второй продажи порции в шприце. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerState.cs | Добавлены идентификаторы порции и физического шприца в проекцию товара. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerTransactions.cs | Повторная цена C01 и запрет повторной продажи PortionId, без изменений проводки денег. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerPriceAndProgressionTests.cs | Прежнее одноразовое ожидание обновлено по прямому разрешению под $10→$8. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerSyringeTests.cs | Новые регрессии повторной продажи и общего PortionId. |
| C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerSyringeTests.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureFieldKit.cs | Проверка экземпляра до действий, прогресс/отмена/упаковка, убраны бесплатные запасы. |
| C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureNpc.cs | Адаптер существующего забора к проверяемому экземпляру, сохранён timestamp анимации. |
| C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureSyringeBindings.cs | Новая часть FieldKit: серверная проверка выбранного экземпляра и восстановление привязки. |
| C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureSyringeBindings.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\InventoryModel.cs | Перенос того же экземпляра, запрет merge/повторного добавления ItemId. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\ItemStack.cs | Метаданные экземпляра и тип шприца в per-type информации. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\OnlyVolunteers.Inventory.Core.asmdef | Ссылка на существующий Buyers Core для единственного API цен; engine-free сохранён. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeInstance.cs | Новые данные экземпляра/порции и чистые правила привязки/отмены/упаковки. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeInstance.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeSaveBlock.cs | Новый блок существующего сейва, включая данные мировых drops; без денег. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeSaveBlock.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeSaleRules.cs | Новый pure C01 confirm/receipt, возврат/списание, один вызов payout. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\SyringeSaleRules.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\DailySyringeFindRules.cs | Новая ежедневная выдача 06:00 и данные авторских дополнительных точек. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\DailySyringeFindRules.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\G48SyringePriceLookup.cs | Новый адаптер одного lookup G48 с aliases C01. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Core\G48SyringePriceLookup.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\ItemDatabase.asset | Добавлены ссылки на два новых определения шприцев. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_SyringeBlood_G49.asset | Новое определение 303, blood, размер 1, stack 1, цена из API. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_SyringeBlood_G49.asset.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_SyringeAnaesthesia_G49.asset | Новое определение 304, anaesthesia, размер 1, stack 1, цена из API. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_SyringeAnaesthesia_G49.asset.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\ItemDefinition.cs | Тип шприца, ограничение stack и чтение цены по ID. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\ItemStackSerializers.cs | FishNet round-trip экземпляра, PersonId, PortionId и состояния содержимого. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\LocalInventory.cs | Pickup/drop переносит метаданные вместо создания нового экземпляра. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\OfflineWorldItem.cs | Хранение и выдача того же экземпляра локального drop. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\WorldItem.cs | Серверные метаданные экземпляра для защищённого NetworkInventory hook. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Tests\EditMode\OnlyVolunteers.Inventory.Tests.asmdef | Ссылка для тестирования реального API цен Buyers. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Tests\EditMode\SyringeRulesTests.cs | 25 новых EditMode случаев правил, payout, save/load, находок и G48. |
| C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Tests\EditMode\SyringeRulesTests.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OnlyVolunteers.Operation.Core.asmdef | Ссылка на engine-free данные предметных экземпляров. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationState.cs | Состояние экземпляров/порций в существующем сейве; запрещён забор из трупа. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationTargets.cs | Добавлены причины отказа без перенумерации старых enum. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationSyringeRules.cs | Новые проверяемые входы перед FillBlood и инъекцией, без сброса счётчика. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationSyringeRules.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\NetworkOperationTable.cs | Минимальные серверные проверки, перенос PortionId в пакет и сохранение экземпляра при смене NPC. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationHud.cs | Текст двух отказов, без изменения UI layout. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Scripts\OperationPhysicalItem.cs | Метаданные физического экземпляра в snapshot и подпись пустого шприца. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Tests\OnlyVolunteers.Operation.Tests.asmdef | Ссылка на экземпляры для реальных operation-тестов. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Tests\OperationRulesTests.cs | Прежнее ожидание забора из трупа исправлено по прямому разрешению. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Tests\OperationSyringeTests.cs | 6 новых тестов применения/лимитов/отмены/операционного сейва. |
| C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Tests\OperationSyringeTests.cs.meta | Новая Unity identity соответствующего файла; старые GUID не менялись. |
| C:\Dev\Game\Working\Tests\G49\G49.Tests.csproj | Связанные оригинальные исходники Buyers/Inventory для чистых .NET проверок. |
| C:\Dev\Game\Working\Tests\G49\Compile-G49.py | Roslyn-проверка реальных исходников с текущими asmdef в памяти, без второго Unity. |
| C:\Dev\Game\Working\Tests\G49\Verify-G49Files.py | Этот проверяющий скрипт; абсолютные пути и sha256 исходников. |
| C:\Dev\Game\docs\reports\SYRINGE_RULE_G49_RU.md | Основной отчёт для Феди, правила → тесты, ограничения и плейтест. |
| C:\Dev\Game\docs\reports\SYRINGE_RULE_G49_HOOKS_RU.md | Часть отчёта: точные НЕ применённые вставки для Claude. |
| C:\Dev\Game\docs\reports\SYRINGE_RULE_G49_FILES.md | Этот перечень всех файлов и причин изменений. |

## Локальные результаты и генерируемые файлы проверки

C:\Dev\Game\Temp\bin\Debug\Assembly-CSharp.dll
C:\Dev\Game\Temp\bin\Debug\Assembly-CSharp.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Buyers.Core.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Buyers.Core.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Buyers.Tests.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Buyers.Tests.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Capture.Core.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Capture.Core.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Economy.Core.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Economy.Core.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.Core.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.Core.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.Tests.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Inventory.Tests.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Operation.Core.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Operation.Core.pdb
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Operation.Tests.dll
C:\Dev\Game\Temp\bin\Debug\OnlyVolunteers.Operation.Tests.pdb
C:\Dev\Game\Temp\G49\1nzxwmfe.pli\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\2h3iqj0l.ola\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\5ke5bjbb.vey\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\aalw542j.ipp\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\c1h35yuj.4ys\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\lwtuv2jj.5vq\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_10972_20261028_165623_271.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_11984_20261028_171319_732.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_13936_20261028_171324_272.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_14772_20261028_165442_712.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_15408_20261028_165433_171.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_17376_20261028_171610_840.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_17536_20261028_165238_388.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_17684_20261028_170400_470.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_17684_20261028_170400_470_510a233a02152a4c99ed330e257c6add-x64_AdminInstall.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_18720_20261028_171318_088.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_20088_20261028_165627_243.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_20136_20261028_165441_473.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_20972_20261028_164839_187.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_21320_20261028_165619_942.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_21596_20261028_165624_852.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_21716_20261028_165626_468.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_22564_20261028_165433_882.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_22604_20261028_165256_074.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_22660_20261028_170358_524.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_23028_20261028_164828_881.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_23028_20261028_164828_950.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_23268_20261028_165622_459.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_23364_20261028_170359_581.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_23908_20261028_171317_358.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24468_20261028_165436_041.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24728_20261028_171321_407.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24780_20261028_165621_012.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24864_20261028_170356_833.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24920_20261028_164420_735.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_24924_20261028_165621_770.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_25104_20261028_171323_510.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_25144_20261028_165437_263.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_25244_20261028_164419_826.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_25352_20261028_170406_678.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_2728_20261028_170354_990.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_27440_20261028_171318_824.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_27672_20261028_170404_857.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_28864_20261028_171320_583.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_29488_20261028_171325_132.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_4088_20261028_165624_071.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_4496_20261028_165434_592.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_5856_20261028_170405_807.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_7792_20261028_165440_397.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_8208_20261028_165438_491.log
C:\Dev\Game\Temp\G49\Microsoft.NET.Workload_9808_20261028_165628_025.log
C:\Dev\Game\Temp\G49\mtymcya4.t1g\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\plpfkfkm.tar\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\pxvqtqmz.oce\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\szwfgij5.op2\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\unity-compile-check\f82bf4c7afc2.targets
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\1\Microsoft.Unity.Analyzers.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\2\Unity.Properties.SourceGenerator.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\2\Unity.SourceGenerators.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\2\Unity.UIToolkit.SourceGenerator.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\3\Unity.Analyzers.Common.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\4\Unity.Analyzers.LongLiving.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\5\Microsoft.Extensions.Logging.Generators.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\5\System.Text.Json.SourceGeneration.dll
C:\Dev\Game\Temp\G49\VBCSCompiler\AnalyzerAssemblyLoader\a343366ded57488aa04a0775e0038120\6\FishNet.CodeAnalysis.Analyzers.dll
C:\Dev\Game\Temp\G49\x5uo4xyb.tjp\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\G49\ywrbmyxz.0fs\microsoft.net.workloads.10.0.400.msi.x64\10.403.0\microsoft.net.workloads.10.0.400.msi.x64.10.403.0.nupkg
C:\Dev\Game\Temp\obj\Assembly-CSharp\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.assets.cache
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.dll
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.pdb
C:\Dev\Game\Temp\obj\Assembly-CSharp\Assembly-CSharp.sourcelink.json
C:\Dev\Game\Temp\obj\Assembly-CSharp\project.assets.json
C:\Dev\Game\Temp\obj\Assembly-CSharp\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\OnlyVolunteers.Buyers.Core.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Core\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\OnlyVolunteers.Buyers.Tests.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Buyers.Tests\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\OnlyVolunteers.Capture.Core.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Capture.Core\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\OnlyVolunteers.Economy.Core.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Economy.Core\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\OnlyVolunteers.Inventory.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\OnlyVolunteers.Inventory.Core.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Core\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\OnlyVolunteers.Inventory.Tests.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Inventory.Tests\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\OnlyVolunteers.Operation.Core.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Core\project.nuget.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\.NETStandard,Version=v2.1.AssemblyAttributes.cs
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.assets.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.AssemblyReference.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.CoreCompileInputs.cache
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.FileListAbsolute.txt
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.nuget.dgspec.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.nuget.g.props
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.csproj.nuget.g.targets
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.dll
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.pdb
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\OnlyVolunteers.Operation.Tests.sourcelink.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\project.assets.json
C:\Dev\Game\Temp\obj\OnlyVolunteers.Operation.Tests\project.nuget.cache
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\.workloadAdvertisingManifestSentinel10.0.400
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\10.0.401.aspNetCertificateSentinel
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\10.0.401.dotnetFirstUseSentinel
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\10.0.401.toolpath.sentinel
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\10.0.401_IsDockerContainer.dotnetUserLevelCache
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\10.0.401_MachineId.dotnetUserLevelCache
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\MachineId.v1.dotnetUserLevelCache
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\sdk-advertising\10.0.400\microsoft.net.workloads\10.0.403\microsoft.net.workloads.workloadset.json
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\sdk-advertising\10.0.400\microsoft.net.workloads\AdvertisedManifestFeatureBand.txt
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\sdk-advertising\10.0.400\microsoft.net.workloads\workloadVersion.txt
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\TelemetryStorageService\20261028141612_922e611efe8a4662bd11c9db73a008fa.trn
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\TelemetryStorageService\20261028141612_b8573b735d0045cb9d4f12f1f15cca7a.trn
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\TelemetryStorageService\20261028141612_de379f7e4e874331949806f0505be1ec.trn
C:\Dev\Game\Working\Tests\G49\.dotnet\.dotnet\TelemetryStorageService\20261028141612_e03d54e8675349f3a70489e109f13ced.trn
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\cs\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\cs\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\cs\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\cs\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\cs\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\de\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\de\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\de\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\de\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\de\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\es\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\es\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\es\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\es\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\es\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\fr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\fr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\fr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\fr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\fr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\G49.Tests.deps.json
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\G49.Tests.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\G49.Tests.pdb
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\G49.Tests.runtimeconfig.json
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\it\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\it\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\it\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\it\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\it\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ja\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ja\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ja\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ja\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ja\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ko\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ko\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ko\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ko\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ko\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.TestPlatform.CommunicationUtilities.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.TestPlatform.CoreUtilities.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.TestPlatform.CrossPlatEngine.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.TestPlatform.PlatformAbstractions.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.TestPlatform.Utilities.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.VisualStudio.CodeCoverage.Shim.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.VisualStudio.TestPlatform.Common.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Microsoft.VisualStudio.TestPlatform.ObjectModel.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\Newtonsoft.Json.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\nunit.engine.api.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\nunit.engine.core.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\nunit.engine.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\nunit.framework.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\NUnit3.TestAdapter.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\NUnit3.TestAdapter.pdb
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pl\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pl\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pl\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pl\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pl\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pt-BR\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pt-BR\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\pt-BR\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ru\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ru\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ru\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ru\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\ru\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\testcentric.engine.metadata.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\testhost.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\testhost.exe
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\tr\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\tr\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\tr\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\tr\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\tr\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hans\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hans\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hans\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CommunicationUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CoreUtilities.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hant\Microsoft.TestPlatform.CrossPlatEngine.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hant\Microsoft.VisualStudio.TestPlatform.Common.resources.dll
C:\Dev\Game\Working\Tests\G49\bin\Release\net8.0\zh-Hant\Microsoft.VisualStudio.TestPlatform.ObjectModel.resources.dll
C:\Dev\Game\Working\Tests\G49\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\repository_signatures_5.0.0.dat
C:\Dev\Game\Working\Tests\G49\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\service_index.dat
C:\Dev\Game\Working\Tests\G49\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_data_base.dat
C:\Dev\Game\Working\Tests\G49\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_data_update.dat
C:\Dev\Game\Working\Tests\G49\http-cache\670c1461c29885f9aa22c281d8b7da90845b38e4$ps_api.nuget.org_v3_index.json\vuln_index.dat
C:\Dev\Game\Working\Tests\G49\obj\G49.Tests.csproj.nuget.dgspec.json
C:\Dev\Game\Working\Tests\G49\obj\G49.Tests.csproj.nuget.g.props
C:\Dev\Game\Working\Tests\G49\obj\G49.Tests.csproj.nuget.g.targets
C:\Dev\Game\Working\Tests\G49\obj\project.assets.json
C:\Dev\Game\Working\Tests\G49\obj\project.nuget.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\.NETCoreApp,Version=v8.0.AssemblyAttributes.cs
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.AssemblyInfo.cs
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.AssemblyInfoInputs.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.assets.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.csproj.AssemblyReference.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.csproj.CoreCompileInputs.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.csproj.FileListAbsolute.txt
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.csproj.Up2Date
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.dll
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.GeneratedMSBuildEditorConfig.editorconfig
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.genruntimeconfig.cache
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.pdb
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\G49.Tests.sourcelink.json
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\ref\G49.Tests.dll
C:\Dev\Game\Working\Tests\G49\obj\Release\net8.0\refint\G49.Tests.dll
C:\Dev\Game\Working\Tests\G49\path-verification.json
C:\Dev\Game\Working\Tests\G49\Results\pure-after-hooks.trx
C:\Dev\Game\Working\Tests\G49\Results\pure-before-hooks.trx
C:\Dev\Game\Working\Tests\G49\Results\pure-final.trx
C:\Dev\Game\Working\Tests\G49\Results\unity-editmode-all.json
C:\Dev\Game\Working\Tests\G49\Results\unity-editmode-final.json
