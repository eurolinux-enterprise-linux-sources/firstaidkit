/*
* First Aid Kit - diagnostic and repair tool for Linux
* Copyright (C) 2008 Joel Andres Granados <jgranado@redhat.com>
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*
*/


#include <Python.h>
#include <assert.h>
#include <string.h>
#include "parted/parted.h"

/*
 * Simple representation of the partition.
 */
typedef struct{
    int partnum;
    PedSector partstart;
    PedSector partend;
} partElem;


/*
 * Helper function
 */

/*
 * Returns a disk with the path of the device.
 */
static PedDisk *
_getDiskFromPath(char * path){
    PedDevice * dev;
    PedDisk * disk;
    /* Try to create the device with the path */
    dev = ped_device_get(path);
    if(dev == NULL)
        return NULL;

    /* Read the partition table off of the device */
    disk = ped_disk_new(dev);
    if(disk == NULL)
        return NULL;

    return disk;
}

/*
 * Return the partition type.
 */
static PedPartitionType
_disk_get_part_type_for_sector (PedDisk* disk, PedSector sector)
{
        PedPartition*   extended;

        extended = ped_disk_extended_partition (disk);
        if (!extended
            || !ped_geometry_test_sector_inside (&extended->geom, sector))
                return 0;

        return PED_PARTITION_LOGICAL;
}

/*
 * Create a python list from one partElement struct
 */
static PyObject *
_getPPartList( int partnum, int partstart, int partend ){
    PyObject * num, * start, * end;
    PyObject * list;
    /*
    * Create a new temporary list.  and add all the related values 
    */
    num = PyString_FromFormat("%d",partnum);
    start = PyLong_FromLong(partstart);
    end = PyLong_FromLong(partend);
    list = PyList_New(3);
    if(num == NULL || start == NULL || end == NULL ||
            list == NULL ||
            PyList_SetItem(list, 0, num) == -1 ||
            PyList_SetItem(list, 1, start) == -1 ||
            PyList_SetItem(list, 2, end) == -1){
        goto handle_error;
    }
    return list;

    handle_error:

    Py_XDECREF(num);
    Py_XDECREF(start);
    Py_XDECREF(end);
    Py_XDECREF(list);
    return NULL;
}

/*
 * Create a array of partElem with the python list
 */
static partElem
_getCPartList( PyObject * list ){
    partElem _list = {0};

    // check that its a list.
    if(!PyList_Check(list)){
        PyErr_SetString(PyExc_StandardError, 
                "Error malformed argument, list does not contian lisit.");
        return _list;
    }

    // check that it has three elements.
    if(PyList_Size(list) < 3){
        PyErr_SetString(PyExc_StandardError, 
                "Error Malformed argument, contained list is to small.");
        return _list;
    }

    // Populate the _partList array.
    _list.partnum = PyLong_AsLong( PyNumber_Long(PyList_GetItem(list, 0)) );
    _list.partstart = PyLong_AsLong( PyList_GetItem(list, 1) );
    _list.partend = PyLong_AsLong( PyList_GetItem(list, 2) );
    if( PyErr_Occurred())
        _list.partnum = '\0';
    return _list;
}

static int
MEGABYTE_SECTORS (PedDevice* dev)
{
        return PED_MEGABYTE_SIZE / dev->sector_size;
}

/*
 * Tries to recover the partition part in the disk disk.  Reutrns null if it
 * was not possible, or the partition if it was.
 */
static PedPartition * 
add_partition(PedDisk * disk, partElem part){

    //PedDisk * clone;
    PedSector s;
    PedGeometry * probed;
    PedGeometry sect_geom;
    PedGeometry entire_dev;
    PedPartition  * parttemp = NULL;
    PedConstraint disk_constraint, * part_constraint;
    PedPartitionType part_type;
    PedFileSystemType * fs_type;

    /* Initialize the entire_dev geom for the constraint calculation */
    ped_geometry_init(&entire_dev, disk->dev, 0, disk->dev->length);
    part_type = _disk_get_part_type_for_sector (disk, (part.partstart + part.partend) / 2);


    /* The end is a temporary hack until we get the method of search done */
    for (s = part.partstart; s < part.partstart+(part.partend-part.partstart)/10; s++) {

        /* Get a part from the specific s sector with the device constraint */
        ped_geometry_init (&sect_geom, disk->dev, s, 1);
        ped_constraint_init (&disk_constraint, ped_alignment_any, ped_alignment_any,
                &sect_geom, &entire_dev, 1, disk->dev->length);

        parttemp = ped_partition_new (disk, part_type, NULL, s, part.partend);
        if(!parttemp){
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(&disk_constraint);
            parttemp = NULL;
            continue;
        }


        /* add the partition to the disk */
        ped_exception_fetch_all(); //dont show errors
        if(!ped_disk_add_partition(disk, parttemp, &disk_constraint)){
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(&disk_constraint);
            parttemp = NULL;
            continue;
        }
        ped_exception_leave_all();// show errors.

        /* try to detect filesystem in the partition region */
        fs_type = ped_file_system_probe(&parttemp->geom);
        if(!fs_type){
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(&disk_constraint);
            parttemp = NULL;
            continue;
        }

        /* try to find the exact region the filesystem ocupies */
        probed = ped_file_system_probe_specific(fs_type, &parttemp->geom);
        if(!probed){
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(&disk_constraint);
            ped_geometry_destroy(probed);
            parttemp = NULL;
            continue;
        }

        /* see if probed is inside the partition region */
        if(!ped_geometry_test_inside(&parttemp->geom, probed)) {
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(&disk_constraint);
            ped_geometry_destroy(probed);
            parttemp = NULL;
            continue;
        }

        /* create a constraint for the probed region */
        part_constraint = ped_constraint_exact (probed);

        /* set the region for the partition */
        if (!ped_disk_set_partition_geom (parttemp->disk, parttemp, part_constraint,
                                          probed->start, probed->end)) {
            ped_disk_remove_partition(disk, parttemp);
            ped_constraint_done(part_constraint);
            ped_constraint_done(&disk_constraint);
            ped_geometry_destroy(probed);
            parttemp = NULL;
            continue;
        }
        ped_partition_set_system(parttemp, fs_type);
        ped_disk_commit(disk);
        ped_disk_commit_to_dev(disk);
        ped_disk_commit_to_os(disk);
        break;
    }
    return parttemp;
}

/* Pythong facing functions.
 *
 * Returns a dictionary of the form { DISK : [None, None, None, None] ...}
 */
static PyObject *
undelpart_getDiskList(PyObject * self, PyObject * args){

    PedDevice * dev;

    PyObject * dict;
    PyObject * list;
    PyObject * diskName;

    int i;

    dict = PyDict_New();
    if(dict == NULL){
        PyErr_SetString(PyExc_StandardError, "Error creating a new dictionary.");
        goto handle_error;
    }

    /* Search for the disks on the system */
    ped_device_probe_all();

    for(dev=ped_device_get_next(dev); dev ; dev=ped_device_get_next(dev)){
        /*
         * Build the list for this particular disk and fill it with Python
         * None Objects. 
         */
        list = PyList_New(4);
        if(list == NULL){
            PyErr_SetString(PyExc_StandardError, "Error creating a new list.");
            goto handle_error;
        }
        for(i=0 ; i < 4 ; i++){ //We set all items to None.
            if(PyList_SetItem(list, i, Py_None) == -1){
                PyErr_SetString(PyExc_StandardError,
                        "Error setting up the None valued list.");
                goto handle_error;
            }
        }

        /*
         * Take the name out of the PedDevice structure and place it as a
         * dictionary key.  Use the device path.
         */
        diskName = Py_BuildValue("s", dev->path);
        if(diskName == NULL){
            PyErr_SetString(PyExc_StandardError,
                    "Error creating key for dictionary.");
            goto handle_error;
        }

        if(PyDict_SetItem(dict, diskName, list) == -1){
            PyErr_SetString(PyExc_StandardError,
                    "Error while creating the dictionary entry");
            goto handle_error;
        }
    }

    /* If the dictionary's length is 0, something is wrong. */
    if(PyDict_Size(dict) == 0){
        PyErr_SetString(PyExc_StandardError,
                "libparted was unable to get a disk list. Are you root?");
        goto handle_error;
    }

    ped_device_free_all();
    return dict;

    handle_error:
    assert(PyErr_Occurred());

    Py_XDECREF(diskName);
    Py_XDECREF(list);
    Py_XDECREF(dict);
    ped_device_free_all();

    return NULL;
}

/*
 * Returns a list of partitions that are present in the disk but not in its
 * partition table. If the disk does not exist it errors. If the disk
 * has no rescueable partitions it returns a void list.  It is a list of 
 * possible partitions,  it will NOT check for rescuability.
 */
static PyObject *
undelpart_getRescuable(PyObject * self, PyObject * args){

    PedDisk  * disk;
    PedPartition * part;

    PyObject * tempList;
    PyObject * partitions;

    char * path;

    if(!PyArg_ParseTuple(args, "s", &path)){
        PyErr_SetString(PyExc_TypeError, "Argument is not a String");
        goto handle_error;
    }

    /* Build the empty list*/
    partitions = PyList_New(0);
    if(partitions == NULL){
        PyErr_SetString(PyExc_StandardError, "Error creating a new list.");
        goto handle_error_destroy_disk;
    }

    /* create the disk */
    disk = _getDiskFromPath(path);
    if(disk == NULL){
        PyErr_SetString(PyExc_StandardError, "Error reading disk information.");
        goto handle_error_destroy_disk;
    }

    /*
     * We start looking for the partitions.  The partitions will be detected if
     * the numpart is less than 1.  The basic idea is to traverse all the partitions
     * and look for holes in between.
     */
    for(part = ped_disk_next_partition(disk, NULL); part ;
            part = ped_disk_next_partition(disk, part) ){
        // All partitions with partnum less than 1 is a possibility.
        if(part->num < 1 && part->geom.start < part->geom.end){
            /* create the python object */
            tempList = _getPPartList(part->num, part->geom.start, part->geom.end);
            /* Append the list to the return value */
            if(tempList == NULL || PyList_Append(partitions, tempList) == -1){
                PyErr_SetString(PyExc_StandardError,
                        "Error creating the partition information.");
                goto handle_error_destroy_disk;
            }
        }
    }
    ped_disk_destroy(disk);
    ped_device_free_all();

    return partitions;

    handle_error_destroy_disk:
        ped_disk_destroy(disk);

    handle_error:
        assert(PyErr_Occurred());

        Py_XDECREF(partitions);
        Py_XDECREF(tempList);

        ped_device_free_all();
        return NULL;
}

/*
 * Returns a list of valid partitions at time of scan.
 */
static PyObject *
undelpart_getPartitionList(PyObject * self, PyObject * args){

    PedDisk * disk;
    PedDevice * dev;
    PedPartition * part; //libparted object

    PyObject * partList; //python list of partitions
    PyObject * tempList; //python temporary object to hold the temprorary list.

    char * path;

    if(!PyArg_ParseTuple(args, "s", &path)){
        PyErr_SetString(PyExc_TypeError, "Argument is not a String");
        goto handle_error;
    }

    /* create the disk an dev */
    disk = _getDiskFromPath(path);
    if(disk == NULL){
        PyErr_SetString(PyExc_StandardError, "Error reading disk information.");
        goto handle_error;
    }
    dev = disk->dev;

    /* Create the python list that we are to fill */
    partList = PyList_New(0);
    if(partList == NULL){
        PyErr_SetString(PyExc_StandardError, "Error creating a new list.");
        goto handle_error;
    }

    /* Get all the active partitions from disk */
    for(part = ped_disk_next_partition(disk, NULL) ;
            part ; part = ped_disk_next_partition(disk, part)){
        if(part->num < 0)
            continue;

        tempList = _getPPartList(part->num,
                part->geom.start,
                part->geom.end);
        /* Append the list to the return value */
        if(tempList == NULL || PyList_Append(partList, tempList) == -1){
            PyErr_SetString(PyExc_StandardError,
                    "Error appending the partition to the list.");
            goto handle_error;
        }
    }
    ped_device_free_all();

    return partList;

    handle_error:
    assert(PyErr_Occurred());

    Py_XDECREF(partList);
    Py_XDECREF(tempList);

    ped_device_free_all();

    return NULL;
}

/*
 * On a specific disk try to rescue a list of partitions.  Return the list of partitions
 * that was recovered.  The partitions should be in the [[partNum, start, end]...]
 * format.
 */
static PyObject *
undelpart_rescue(PyObject * self, PyObject * args){

    PedDisk * disk;
    PedPartition * part;

    PyObject * partList;
    PyObject * rescuedParts;
    PyObject * tempList;

    partElem * _partList = NULL;
    char * path;
    int partListSize = 0;
    int i;

    /* Check the arguments */
    if(!PyArg_ParseTuple(args, "sO", &path, &partList)){
        PyErr_SetString(PyExc_TypeError, "Arguments are not valid (String, List)");
        goto handle_error;
    }
    if(! PyList_Check(partList)){
        PyErr_SetString(PyExc_TypeError,
                "The object that was passed is not a list.");
        goto handle_error;
    }

    /* Build the empty list, this is the return value. */
    rescuedParts = PyList_New(0);
    if(rescuedParts == NULL){
        PyErr_SetString(PyExc_StandardError, "Error creating a new list.");
        goto handle_error;
    }

    /* Put the values of the list into a array of partElem */
    partListSize = PyList_Size(partList);
    _partList = malloc(sizeof(partElem)*partListSize+1);
    if(!_partList){
        PyErr_SetString(PyExc_StandardError, "Error allocating memory.");
        goto handle_error;
    }
    for(i=0; i < partListSize ; i++){
        _partList[i] = _getCPartList(PyList_GetItem(partList, i));
        if( PyErr_Occurred() || _partList[i].partnum == '\0'){
            goto handle_error;
        }
    }
    _partList[partListSize].partnum = '\0';

    /* create the disk an dev */
    disk = _getDiskFromPath(path);
    if(disk == NULL){
        PyErr_SetString(PyExc_StandardError, "Error reading disk information.");
        goto handle_error;
    }

    /* Try to add each partition. */
    for(i=0 ; _partList[i].partnum ; i++){
        part = add_partition(disk, _partList[i]);
        if(!part){
            // could not rescue this partition. sorry
            continue;
        }else{
            tempList = _getPPartList(part->num, part->geom.start, part->geom.end);
            /* Append the list to the return value */
            if(tempList == NULL || PyList_Append(rescuedParts, tempList) == -1){
                PyErr_SetString(PyExc_StandardError,
                        "Error creating the partition information.");
                goto handle_error;
            }
        }
    }
    ped_disk_destroy(disk);
    free(_partList);
    ped_device_free_all();

    return rescuedParts;

    handle_error:
    assert(PyErr_Occurred());

    free(_partList);
    ped_device_free_all();

    return NULL;
}

static struct PyMethodDef undelpart_methods [] = {
    { "getDiskList",
        (PyCFunction)undelpart_getDiskList,
        METH_VARARGS, "Generaly returns the system disk list.  Receives nothing." },
    { "getRescuable",
        (PyCFunction)undelpart_getRescuable,
        METH_VARARGS, "Get a list of partitions from a specific disk that might "
            "be rescuable.  It returns the partitions that are not in the partition "
            "table but where present after a disk scan.  It expects the disk name."},
    { "getPartitionList",
        (PyCFunction)undelpart_getPartitionList,
        METH_VARARGS, "Get the partition list off of a certain disk.  This is intended "
            "to be used as a backup.  It returns the number of the partition, start "
            "sector and the end sector."},
    {"rescue",
        (PyCFunction)undelpart_rescue,
        METH_VARARGS, "Try to put the list of rescuable partitions into the partition "
            "table.  If the partitions are already there, nothing will be done.  A list "
            "of rescued partitions is returned.  This does NOT delete any partitions."}
};

void init_undelpart(void){
    (void) Py_InitModule("_undelpart", undelpart_methods);
}
