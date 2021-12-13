contents = [
{
		"date" : 1638806100,
		"title" : "Halo Infinite",
		"id" : "GUnjcm9TYnk",
		"category" : "Video Games",
		"score" : "80",
		"rated" : True
},
{
		"date" : 1636142058,
		"title" : "Eternals",
		"id" : "5P4gL59Z0zg",
		"category" : "Movies",
		"score" : "60",
		"rated" : True
	}
]

mm_obj = {
	"date" : 1637512382,
	"title" : "Arcane",
	"id" : "WIvU9VEgxUc",
	"category" : "TV Shows",
	"score" : "95",
	"rated" : True
}

temp = {
	"category" : "",
	"score" : "",
	"rated" : False
}

for index in range(len(contents) + 1):
	if index < len(contents) and mm_obj["date"] < contents[index]["date"]:
		continue
	
	print("Inserting at index " + str(index))
	mm_obj.update(temp)
	contents.insert(index, mm_obj)
	break


for obj in contents:
	print(obj["title"])

print("done")