# [Why Dbt?](https://www.getdbt.com)

To prepare raw data for analysis is a highly manual and technical process. Analysts and data engineers spend hours orchestrating the data transformation pipeline and then more time checking for accuracy. Data needs to be reliable for making decisions, and even the slight of inaccuracies can lead to incorrect insights. dbt (data build tool) addresses this by automating the transformation process, making it faster and less error-prone.

### <b> [Tool for streamlined builds](#tool-for-streamlined-builds)</b>

Just as a washing machine cleans clothes more thoroughly and with less effort than hand-washing, dbt automates data checks, swiftly identifying errors that could take humans hours to find. It uses SQL, to handle common tasks such as renaming columns or merging tables. But dbt does not stop there - it brings in additional firepower for more challenging tasks.

An extension in dbt, dbt-fal, is analogous to the attachments for a power drill. It is specifically designed to run Python scripts for complex tasks that SQL alone can't manage, like fuzzy matching, which is crucial for cleaning up data that's not quite consistent. Some users prefer dbt with its SQL capabilities (because it's familiar and powerful for most data tasks). This can be a good approach, but when dealing with more complicated data issues or needing advanced analytics, the addition of Python through dbt-fal provides that extra layer of sophistication.

### <b>[Structures data quality tests](#structures-data-quality-tests)</b>

As data is transformed and prepared for analysis by dbt, it can work alongside Great Expectations to run more comprehensive tests on the data. Think of it as a meticulous editor going through a draft, not just for spelling errors, but also checking the story flow and facts. This ensures the data is not just transformed but is of high quality and ready for reliable decision-making.

The dbt docs functionality is an intelligent catalog that keeps track of all transformations applied to the data, offering a transparent view of its journey. This is incredibly useful for teams to understand and trust their data pipelines, much like how a detailed map helps travelers understand their route and terrain. It means that each team member can easily see what's happened to the data without having to dig through lines of code.
