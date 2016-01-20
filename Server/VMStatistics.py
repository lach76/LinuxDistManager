import os
import sys
import datetime

def combineGatheringData(fr, to, display_only):
    try:
        intFromDate = int(fr)
        intToDate = int(to)
    except:
        return None, None

    platform_dict = {}
    platform_title = ""
    for startDate in range(intFromDate, intToDate):
        dir_path = "./%d" % startDate
        for file in os.listdir(dir_path):
            filepath = os.path.join(dir_path, file) 
            if not platform_dict.has_key(file):
                platform_dict[file] = {} 
            with open(filepath, "r") as res_file:
                readlines = res_file.readlines()

            if len(platform_title) < readlines[0]:
                platform_title = readlines[0].strip()

            if not display_only:
                for line in readlines[1:]:
                    line = line.strip()
                    items = line.split('|')
                    keyname = "%d%s" % (startDate, items[0])
                    platform_dict[file][keyname] = line.split('|')

    return platform_title.split('|'), platform_dict

def compute_statistics(data_dict, statlist):
    result = {}
    for platform, platform_value in data_dict.items():
        result[platform] = {}
        for stat_index in statlist:
            min_dict = {}
            max_dict = {}
            min_value = None
            max_value = None
            for date_key, usage_list in platform_value.items():
                if not usage_list[stat_index].isdigit():
                    tmp = usage_list[stat_index].split(';')
                    usage_list[stat_index] = tmp[0]
                if min_value is None:
                    min_value = int(usage_list[stat_index])
                    min_dict["time"] = date_key
                    min_dict["value"] = min_value
                if max_value is None:
                    max_value = int(usage_list[stat_index])
                    max_dict["time"] = date_key
                    max_dict["value"] = max_value
                value = int(usage_list[stat_index])
                if value < min_value:
                    min_value = value
                    min_dict["time"] = date_key
                    min_dict["value"] = min_value
                if value > max_value:
                    max_value = value
                    max_dict["time"] = date_key
                    max_dict["value"] = max_value
           
            result[platform][stat_index] = {"min":min_dict, "max":max_dict}

    return result

def combineDataTimeline(item_dict, itemindexlist, fr, to):
    result = {}
    for startDate in range(int(fr), int(to)):
        for timeindex in range(0, 288):
            timevalue = timeindex * 5
            timevalue = (timevalue / 60) * 100 + timevalue % 60
            timeline_str = "%s%04d" % (startDate, timevalue)

            itemvalue_list = [0] * len(itemindexlist)
            for dict_key, dict_value in item_dict.items():
                if dict_value.has_key(timeline_str):
                    dict_list = dict_value[timeline_str]
                    for i, get_index in enumerate(itemindexlist):
                        itemvalue_list[i] += int(dict_list[get_index])
           
            result[timeline_str] = itemvalue_list
                     
    return result

VMStatisticsTitle = """
+-------------------------------------------------------+
|  VM Statistics                                        |
|                                                       |
|                                        2015 Simpler   |
+-------------------------------------------------------+
"""
from optparse import OptionParser
import pprint
usage = """usage: %prog -f 20150111 -t 20161201 -i ConnectedSessions"""
if __name__ == "__main__":
    print VMStatisticsTitle

    current = datetime.datetime.now()
    default_toDate = "%04d%02d%02d" % (current.year, current.month, current.day)

    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--from", dest="fr", action="store", help="set start date")
    parser.add_option("-t", "--to", dest="to", action="store", default=default_toDate,  help="set end date")
    parser.add_option("-d", "--display", dest="display", action="store_true", default=False, help="display only items")
    parser.add_option("-i", "--items", dest="items", default=[], type=str, action="append", help="set statistics target item -i TIME -i DURATION -i ....")

    (options, args) = parser.parse_args()
    if not (options.fr and (options.display or options.items)):
        parser.print_help()
        print "input arguments are not valid"
        exit()

    item_list, item_dict = combineGatheringData(options.fr, options.to, options.display)
    if options.display:
        pprint.pprint(item_list)
        exit()
            
    itemindexlist = []
    for stat_item in options.items:
        if stat_item in item_list:
            itemindexlist.append(item_list.index(stat_item))

    result_file = open("result_per_vm.csv", "w")
    print "PER VirtualMachine Statistics"
    print ""
    result = compute_statistics(item_dict, itemindexlist)
    title = "%20s  " % "VMName"
    write_line = "VMName"
    for index in itemindexlist:
        title += "%16s " % item_list[index][:16]
        write_line += "|%s(MIN)|%s(MAX)" % (item_list[index], item_list[index])
    print title

    result_file.write(write_line + '\n')
    min_total = [0] * len(itemindexlist)
    max_total = [0] * len(itemindexlist)
    for VMName, VMValue in result.items():
        write_line = "%20s" % VMName[:20]
        line = "%20s  " % VMName[:20]
        for pos, index in enumerate(itemindexlist):
            min_total[pos] += VMValue[index]['min']['value']
            max_total[pos] += VMValue[index]['max']['value']
            line += "   %3d " % VMValue[index]["min"]["value"]
            line += "   %3d      " % VMValue[index]["max"]["value"]

            write_line += "|%d|%d" % (VMValue[index]["min"]["value"], VMValue[index]["max"]["value"])
        result_file.write(write_line + '\n')

        print line

    line = "%20s  " % "Total"
    for i in range(0, len(itemindexlist)):
        line += "   %3d " % min_total[i] 
        line += "   %3d      " % max_total[i]
    print line

    result_file.close()

    result_file = open("result_per_timeline.csv", "w")
    print ""
    print "PER TIME Statistics"
    print ""
    timeline_usage = combineDataTimeline(item_dict, itemindexlist, options.fr, options.to)

    write_line = "timeline"
    for item in itemindexlist:
        write_line += '|%s' % (item_list[item])
    result_file.write(write_line + '\n')

    timeline_list = timeline_usage.keys()
    timeline_list.sort()
    for timeline_key in timeline_list:
        write_line = "%s" % timeline_key
        for i in timeline_usage[timeline_key]:
            write_line += '|%d' % i
        result_file.write(write_line + '\n')
    result_file.close()

    for i, index in enumerate(itemindexlist):
        min_value = None
        max_value = None
        min_date = None
        max_date = None
        for timeline_time, timeline_value in timeline_usage.items():
            if not (min_value and (min_value < timeline_value[i])):
                min_value = timeline_value[i]
                min_date = timeline_time
            if not (max_value and (max_value > timeline_value[i])):
                max_value = timeline_value[i]
                max_date = timeline_time

        print item_list[index]
        print "-----------------"
        print "  * MIN (%d / %s) MAX (%d / %s)" % (min_value, min_date, max_value, max_date)
               

    print "File is generated - result_per_vm.csv, result_per_time.csv"

    """
    data = getMax(platform_dict, "ConnectedSessions")
    print data
    data = getMin(platform_dict, "ConnectedSessions")
    print data
    data = getAvr(platform_dict, "ConnectedSessions")
    print data

    """
